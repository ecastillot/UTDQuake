# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-05-24 14:31:48
#  * @modify date 2025-05-24 14:31:48
#  * @desc [description]
#  */
from http.client import RemoteDisconnected
import queue
import traceback
import threading
import gc
import os
import sqlite3
import time
import obsplus
import warnings
import pandas as pd
from tqdm import tqdm
import concurrent.futures as cf
from obspy.clients.fdsn import Client as FDSNClient 
import logging
from . import utils as fut

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning, module="obspy.io.quakeml.core")

available_events_keys = [
    "minlatitude", "maxlatitude", "minlongitude", "maxlongitude",
    "latitude", "longitude", "minradius", "maxradius",
    "mindepth", "maxdepth",
    "minmagnitude", "maxmagnitude",
    "magnitudetype", "eventtype", 
    "catalog", "contributor", "updatedafter"]

class Client(FDSNClient):
    """
    A bank class for retrieving and calculating rolling statistics on seismic data.

    Inherits from:
        Client: Base class for FDSN web service clients.

    Attributes:
        output (str): Path to the SQLite database file for saving results.
        step (int): Step size for the rolling window in seconds.
    """

    def __init__(self,*args, **kwargs):
        """
        Initializes the Client class by calling the constructor 
        of the base FDSN Client class.

        Parameters:
        *args : variable length argument list
            Positional arguments passed to the base class constructor.
        **kwargs : variable length keyword arguments
            Keyword arguments passed to the base class constructor.
        """
        self.event_id_query_fmt = None
        super().__init__(*args, **kwargs)
        
    def _picks_availability(self, starttime, endtime, eventid_tests=None):
        """
        Check availability of picks and arrivals using multiple query modes.

        The method first attempts to find picks in "natural mode". If unsuccessful,
        it then tries "event ID mode", optionally using test cases.

        Parameters
        ----------
        starttime : UTCDateTime
            Start of the time window to search for picks.
        endtime : UTCDateTime
            End of the time window to search for picks.
        eventid_tests : dict or None, optional
            Optional test cases used when querying by event ID.


        Returns
        -------
        dict
            Dictionary indicating which mode (if any) contains valid picks and arrivals.
            If neither mode succeeds, returns a default structure with `picks=False`.
        """
        natural_mode = self._picks_in_natural_mode(starttime, endtime)
        if natural_mode["picks"]:
            return natural_mode
        else:
            eventid_mode = self._picks_in_eventid_mode(starttime, endtime,tests=eventid_tests)
            if eventid_mode["picks"]:
                return eventid_mode
            else:
                return {
                    "name": None,
                    "mode": None,
                    "picks": False,
                    "arrivals": False,
                    "msg": None
                }
            
    def _picks_in_natural_mode(self,starttime, endtime):
        """
        Attempt to retrieve picks and arrivals using a standard 'natural' query mode.

        This method queries the event catalog within the given time window and checks
        if picks and arrivals are available using `get_events(includearrivals=True)`.

        Parameters
        ----------
        starttime : UTCDateTime
            Start time of the query window.
        endtime : UTCDateTime
            End time of the query window.

        Returns
        -------
        dict
            Dictionary with information about the query result, including:
            - name: Mode name ("natural")
            - mode: Reserved for future use (currently None)
            - picks: Boolean indicating whether picks were found
            - arrivals: Boolean indicating whether arrivals were found
            - msg: Error message, if any
        """
        # Initialize result dictionary with default values
        info = {
            "name": "natural",
            "mode": None,
            "picks": False,
            "arrivals": False,
            "msg": None
        }

        try:
            # Query event catalog including arrivals
            cat = self.get_events(starttime=starttime,
                                    endtime=endtime,
                                    includearrivals=True)
            # Check for a preferred origin to determine if arrivals are present
            pref_origin = cat[0].preferred_origin()
            if pref_origin:
                info["arrivals"] = True

            # Check if any picks exist for the first event in the catalog
            if cat[0].picks:
                info["picks"] = True
        except Exception:
            # If the client does not support includearrivals, record the issue
            info["msg"] = "Client does not support get_events with include_arrivals"

        return info
    
    def _picks_in_eventid_mode(self,starttime, endtime, tests=None):
        """
        Attempt to retrieve picks and arrivals by querying using event IDs.

        This method first queries the catalog to get a reference event, then uses
        various test strategies to construct potential event IDs. It queries again
        using these IDs to check for associated picks and arrivals.

        Parameters
        ----------
        starttime : UTCDateTime
            Start time of the query window.
        endtime : UTCDateTime
            End time of the query window.
        tests : dict or None, optional
            Optional dictionary of test strategies used by `EventIDTester` to generate
            event IDs based on the reference event.

        Returns
        -------
        dict
            Dictionary with information about the result of the query, including:
            - name: Mode name ("eventid")
            - mode: The successful test key used to generate a valid event ID (if any)
            - picks: Boolean indicating whether picks were found
            - arrivals: Boolean indicating whether arrivals were found
            - msg: Error message, if any
        """
        # Initialize result dictionary with default values
        info = {
            "name": "eventid",
            "mode": None,
            "picks": False,
            "arrivals": False,
            "msg": None
        }

        try:
            # Get catalog of events in the given time range
            catalog = self.get_events(starttime=starttime,
                                    endtime=endtime)
        except Exception:
            info["msg"] = "Client does not support get_events"
            return info

        # Select the first event as a reference to generate event IDs
        event = catalog[0]
        eit = fut.EventIDTester(event, tests=tests)

        # Iterate over all test keys to try multiple event ID generation strategies
        for test_key in eit.tests.keys():
            ev_id = eit.get_event_id(test_key)

            if ev_id is not None:
                try:
                    # Try querying by the generated event ID
                    cat = self.get_events(eventid=ev_id)
                    pref_origin = cat[0].preferred_origin()

                    # Check for arrivals
                    if pref_origin:
                        info["arrivals"] = True

                    # Check for picks
                    if cat[0].picks:
                        info["picks"] = True
                        info["mode"] = test_key
                        break  # Exit loop once a valid mode is found
                except Exception:
                    # Ignore failure and continue testing other strategies
                    pass

        return info
    
    def _get_reference_event_time(self, starttime, endtime, 
                                    chunk_seconds=3600,
                                    patience: int = 10):
        """
        Attempt to find the origin time of the first event within a time range.

        This method divides the search time window into chunks and uses a generator
        to iterate through catalogs of events. It returns the origin time of the 
        first event found, or None if no events are available after the specified
        number of chunks (controlled by `patience`).

        Parameters
        ----------
        starttime : str or UTCDateTime
            Start of the search window.
        endtime : str or UTCDateTime
            End of the search window.
        chunk_seconds : int, optional
            Duration of each time chunk in seconds. Default is 3600 (1 hour).
        patience : int, optional
            Maximum number of chunks (iterations) to attempt. Default is 10.

        Returns
        -------
        UTCDateTime or None
            Origin time of the first available event, or None if no event is found
            within the allowed chunks.
        """
        # Create a generator to fetch event catalogs in chunks
        generator = fut.catalog_generator(self, starttime=starttime, endtime=endtime,
                                    chunk_seconds=chunk_seconds,patience=patience)
        origin_time = None

        # Iterate through each catalog chunk
        for catalog in generator:

            if len(catalog) > 0:
                # If at least one event is present, get the origin time of the first
                event = catalog[0]
                origin_time = event.preferred_origin().time
                break

        return origin_time

    def picks_service(self, starttime, endtime, 
                        chunk_seconds=3600,
                        patience: int = 10,
                        eventid_tests=None):
        """
        Determine pick availability for a client that supports the 'event' service.

        This method attempts to find a reference event time within the specified 
        time range by chunking the request window. It then checks for the availability 
        of picks and arrivals using different query modes.

        Parameters
        ----------
        starttime : str or UTCDateTime
            Start of the time range to search for events.
        endtime : str or UTCDateTime
            End of the time range to search for events.
        chunk_seconds : int, optional
            Duration of each time chunk in seconds. Default is 3600 (1 hour).
        patience : int, optional
            Number of chunks to try before giving up. Default is 10.
        eventid_tests : dict or None, optional
            Optional dictionary used to test different event ID strategies.

        Returns
        -------
        dict
            Dictionary indicating the availability of picks and arrivals.

        Raises
        ------
        Exception
            If no events are found or if the 'event' service is not supported.
        """
       
        # Get the list of supported services from the client
        services = list(self.services.keys())

        # Proceed only if 'event' service is supported
        if "event" in services:

            # Try to find a reference event time in the specified range
            ref_event_time = self._get_reference_event_time(starttime, endtime,
                                                            chunk_seconds=chunk_seconds,
                                                            patience=patience)
            # Raise an error if no events were found
            if ref_event_time is None:
                raise Exception("No events found in the specified time range.")

            # Check pick availability within ±60 seconds of the reference event
            picks_avail = self._picks_availability( starttime=ref_event_time - 60,
                                                    endtime=ref_event_time + 60,
                                                    eventid_tests=eventid_tests)
            return picks_avail
        else:
            raise Exception("The client does not support the 'event' service.")

    @staticmethod
    def save_inventory_to_bank(base_path, inventory):
        """
        Saves each network from an ObsPy Inventory to a StationXML file and
        inserts its metadata into a shared SQLite database.

        Parameters
        ----------
        base_path : str
            Path to the folder where files and database will be stored.
        inventory : obspy.Inventory
            The Inventory object containing network/station metadata.
        """
        os.makedirs(base_path, exist_ok=True)
        db_path = os.path.join(base_path, ".stations.db")

        try:
            with sqlite3.connect(db_path) as conn:
                for net in inventory.networks:
                    try:
                        net_code = net.code
                        # Create a new Inventory with just this network
                        single_inv = inventory.select(network=net_code)
                        
                        # Save StationXML
                        xml_path = os.path.join(base_path, f"{net_code}.xml")
                        single_inv.write(xml_path, format="STATIONXML")
                        logger.info(f"Saved XML for network {net_code} at {xml_path}")

                        # Save to DB
                        df = single_inv.to_df()
                        df.to_sql("/stations/index", conn, if_exists="append", index=False)
                        logger.info(f"Saved DB entry for network {net_code}")

                        del df, single_inv
                        gc.collect()

                    except Exception as e:
                        logger.exception(f"Failed to process network {net.code}: {e}")
                        traceback.print_exc()
        except Exception as e:
            logger.exception(f"Could not connect to SQLite DB: {e}")
            traceback.print_exc()

    def save_stations_to_bank(self, base_path, 
                            workers=None, **sta_kwargs):
        """
        Saves station data to a specified base path using parallel threads.

        Parameters
        ----------
        base_path : str
            Base directory where station files will be saved.
        workers : int or None, optional
            Number of worker threads to use. If None, the default from ThreadPoolExecutor is used.
        **sta_kwargs : dict
            Additional keyword arguments passed to the `get_stations` method.
        """
        # Get the list of supported services from the client
        services = list(self.services.keys())
        if "station" not in services:
            raise Exception("The client does not support the 'station' service.")


        # Ensure the base directory exists
        os.makedirs(base_path, exist_ok=True)
        
        if workers is None:
            cpu_cores = os.cpu_count() or 1  # fallback to 1 if cpu_count() returns None
            workers = min(4, cpu_cores)  # max 4 workers or number of cores, whichever is smaller

        # Default to response level if not specified
        if "level" not in sta_kwargs:
            sta_kwargs["level"] = "channel"
        
        # Fetch network-level metadata
        kwargs = sta_kwargs.copy()
        kwargs["level"] = "network"
        net_inv = self.get_stations(**kwargs)
        networks = sorted(set(net.code for net in net_inv))
        
        del net_inv, kwargs

        # SQLite DB path
        db_path = os.path.join(base_path, ".stations.db")

        # Queue for thread-safe database writing
        write_queue = queue.Queue()

        total_networks = len(networks)
        completed = 0
        lock = threading.Lock()  # to safely update the counter

        def db_writer():
            """Dedicated DB writer thread to avoid SQLite locking issues."""
            with sqlite3.connect(db_path) as conn:
                while True:
                    item = write_queue.get()
                    if item is None:
                        break
                    df = item
                    try:
                        df.to_sql("/stations/index", conn, if_exists="append", index=False)
                    except Exception as e:
                        logger.exception(f"DB write error: {e}")
                    write_queue.task_done()

        writer_thread = threading.Thread(target=db_writer)
        writer_thread.start()

        def process_network(network_code):
            nonlocal completed
            net_inv, df = None, None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    local_kwargs = sta_kwargs.copy()
                    local_kwargs["network"] = network_code

                    net_inv = self.get_stations(**local_kwargs)

                    if not net_inv[0].stations:
                        msg = f"No stations found for network {network_code}."
                        break

                    # Save StationXML
                    xml_path = os.path.join(base_path, f"{network_code}.xml")
                    net_inv.write(xml_path, format="STATIONXML")

                    # Convert to DataFrame and queue for DB write
                    df = net_inv.to_df()
                    write_queue.put(df)
                    msg = f"Saved station data for network {network_code} to {xml_path}"
                    break  # success, exit retry loop

                except RemoteDisconnected:
                    time.sleep(2)  # wait before retry
                    msg = f"RemoteDisconnected on {network_code}, attempt {attempt+1}."
                except Exception as e:
                    logger.exception(f"Error processing network {network_code}: {e}")
                    msg = f"Error processing network {network_code}: {e}"
                    break  # unexpected error, stop retrying

            with lock:
                completed += 1
                logger.info(f"Progress: {completed}/{total_networks}, {msg}")
            del df
            del net_inv
            gc.collect()

        if len(networks) <= workers:
            workers = len(networks)  # Use one thread per network if fewer networks than workers
        
        # Run threads
        with cf.ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(process_network, networks)

        # Stop DB writer thread
        write_queue.put(None)
        writer_thread.join()

    def save_events_to_bank(self, base_path,
                        starttime, endtime, 
                        path_structure='{year}/{month}/{day}/{hour}',
                        name_structure='{event_id_end}',
                        chunk_seconds=7200,
                        patience=10,
                        max_n_events=None,
                        eventid_tests=None,
                        calculate_d_az = False,
                        stations_bank_path=None,
                        minlatitude=None,
                        maxlatitude=None, minlongitude=None, maxlongitude=None,
                        latitude=None, longitude=None, minradius=None,
                        maxradius=None, mindepth=None, maxdepth=None,
                        minmagnitude=None, maxmagnitude=None, magnitudetype=None,
                        eventtype=None, includeallorigins=None,
                        includeallmagnitudes=None,
                        catalog=None, contributor=None, updatedafter=None,
                        format='quakeml', 
                        workers=4, 
                        debug=False):
        """
        Save seismic events from a data source to an EventBank on disk.

        Downloads events in chunks and stores them in a structured directory layout.
        Can use either natural mode or eventid-based mode depending on the availability
        of picks.

        Parameters
        ----------
        base_path : str
            Root directory to store the event files.

        starttime, endtime : UTCDateTime or str
            Time window to filter events.

        path_structure : str, optional
            Template for directory layout (default uses year/month/day/hour).

        name_structure : str, optional
            Template for naming individual event files.

        chunk_seconds : int, optional
            Duration (in seconds) of each data chunk window. Default is 7200 (2 hours).

        patience : int, optional
            Number of empty chunks to tolerate before stopping.

        max_n_events : int or None, optional
            Maximum number of events to download. If None, fetch all.

        eventid_tests : dict or None, optional
            Dictionary with test cases for extracting custom event IDs (eventid mode).

        calculate_d_az : bool, optional
            If True, calculate azimuth and distance for each pick in the event.

        stations_bank_path : str or None, optional
            Path to a station bank for calculating azimuth and distance. Mandatory if `calculate_d_az` is True.

        Filtering parameters (all optional) -> check get_events documentation for details
        -----------------------------------
        latitude, longitude, minradius, maxradius,
        minlatitude, maxlatitude, minlongitude, maxlongitude,
        mindepth, maxdepth, minmagnitude, maxmagnitude,
        magnitudetype, eventtype, includeallorigins,
        includeallmagnitudes, catalog, contributor, updatedafter

        format : str, optional
            Output format for the saved events (default is 'quakeml').

        workers : int, optional
            Number of parallel threads to use when saving with eventid mode.

        debug : bool, optional
            Print verbose output if True.
        """

        # Check for available picks
        logger.debug(f"Checking picks availability from {starttime} to {endtime}...")
        logger.info(f"Test")
        ## I need to change all the debug prints to logger.debug
        exit()
        picks_avail = self._picks_availability( starttime=starttime, endtime=endtime,
                                                eventid_tests=eventid_tests)


        if not picks_avail["picks"]:
            raise Exception("No available picks service in the Client.")

        if calculate_d_az and stations_bank_path is None:
            raise Exception("If calculate_d_az is True, stations_bank_path must be provided.")
        elif calculate_d_az and not os.path.exists(stations_bank_path):
            raise Exception(f"Stations bank path {stations_bank_path} does not exist.")
        elif calculate_d_az is None and stations_bank_path is not None:
            warnings.warn(
                "calculate_d_az is None, but stations_bank_path is provided. "
                "This will not be used. Set calculate_d_az=True to use it.",
                UserWarning
            )
        elif calculate_d_az and os.path.exists(stations_bank_path):
            db_path = os.path.join(stations_bank_path, ".stations.db")
            stations = fut.load_stations_metadata_from_bank(db_path=db_path)
            csv_path = os.path.join(base_path, ".bad_stations.csv")
        else:
            stations = None
            csv_path = None

        # Prepare keyword arguments for get_events
        ev_kwargs = {
            k: v for k, v in locals().items()
            if k in available_events_keys and v is not None
        }

        if picks_avail["name"] == "natural":
            ev_kwargs.update({
                "includearrivals": True,
                "includeallorigins": includeallorigins,
                "includeallmagnitudes": includeallmagnitudes
            })
        elif picks_avail["name"] == "eventid":
            ev_kwargs.update({
                "includearrivals": False,
                "includeallorigins": False,
                "includeallmagnitudes": False
            })

        os.makedirs(base_path, exist_ok=True)

        ebank = obsplus.EventBank(
            base_path=base_path,
            path_structure=path_structure,
            name_structure=name_structure,
            format=format
        )


        logger.info(f"Saving events to {base_path} with structure: {path_structure}")

        if stations is not None and picks_avail["name"] == "eventid":
            if debug:
                logger.info(f"Initiating dedicated thread for CSV writing at {csv_path}")

            # if csv_path is not None and picks_avail["name"] == "eventid":
            csv_queue = queue.Queue()
            csv_lock = threading.Lock()
            def csv_writer():
                """Dedicated thread to write bad_inv_data to CSV from queue."""
                while True:
                    item = csv_queue.get()
                    if item is None:
                        break
                    df = item
                    try:
                        with csv_lock:
                            df.to_csv(csv_path, mode="a", index=False, header=not os.path.exists(csv_path))
                    except Exception as e:
                        logger.exception(f"CSV Write Error: {e}")
                    csv_queue.task_done()
            # Start the writer thread
            writer_thread = threading.Thread(target=csv_writer)
            writer_thread.start()

        total_events = 0
        iteration = 0
        id_tests = eventid_tests

        logger.info(f"Starting event download from {starttime} to {endtime}")
        for catalog in fut.catalog_generator(self, starttime=starttime, endtime=endtime,
                                 chunk_seconds=chunk_seconds, debug=debug, 
                                 patience=patience, **ev_kwargs):

            # print(catalog)
            if len(catalog) == 0:
                continue

            # Trim if over the event limit
            if max_n_events is not None:
                remaining = max_n_events - total_events
                if remaining <= 0:
                    break
                elif remaining < len(catalog):
                    catalog.events = catalog.events[:remaining]

            n_events = len(catalog)
            total_events += n_events
            iteration += 1

            logger.info(f"Saving Iter {iteration:<3} ({n_events:>4} events)")
            if stations is not None:
                logger.info(f"Using stations from {stations_bank_path} to recalculate distances and azimuths")

            tic = time.time()


            if picks_avail["name"] == "natural":
                if stations is not None:
                    # Append stations metadata to the catalog
                    catalog,bad_inv_data = fut.append_stations_to_catalog(catalog=catalog, df_stations=stations,
                                                            debug=debug)

                    if not bad_inv_data.empty:
                        bad_inv_data.to_csv(
                            csv_path, mode="a", index=False,
                            header=not os.path.exists(csv_path)
                        )

                        if debug:
                            logger.info(f"Check bad station metadata entries in {csv_path}")

                ebank.put_events(catalog)

            elif picks_avail["name"] == "eventid":
                ev_ids, id_tests =  fut.get_valid_event_ids(catalog=catalog,tests=id_tests)

                def save_single_event(ev_id):
                    single_catalog = self.get_events(eventid=ev_id, **ev_kwargs)

                    if stations is not None:
                        
                        # Append stations metadata to the single event catalog
                        single_catalog, single_bad_inv_data = fut.append_stations_to_catalog(
                                                                catalog=single_catalog, df_stations=stations,
                                                                debug=debug
                                                            )
                        if not single_bad_inv_data.empty:
                            csv_queue.put(single_bad_inv_data)

                    ebank.put_events(single_catalog)

                # for ev_id in ev_ids:
                #     save_single_event(ev_id)
                with cf.ThreadPoolExecutor(max_workers=workers) as executor:
                    executor.map(save_single_event, ev_ids)

                if debug and stations is not None:
                    print(f"Check bad station metadata entries in {csv_path}")
                
            else:
                raise Exception("No way to extract the picks")

            toc = time.time()

            logger.info(
                f"Iter {iteration:<3} ({n_events:>4} events in {toc - tic:.2f} s) | "
                f"Total: {total_events:>4}/{max_n_events}"
            )
                
            if max_n_events is not None and total_events >= max_n_events:
                break
        
        if stations is not None and picks_avail["name"] == "eventid":
            #     # Signal the writer thread to stop
            csv_queue.put(None)
            writer_thread.join()
        
    def save2_events_to_bank(self, base_path,
                       path_structure='{year}/{month}/{day}/{hour}',
                       name_structure='{event_id_end}',
                        chunks=100,
                        max_n_events=None,
                        eventid_tests=None,
                        starttime=None, endtime=None, minlatitude=None,
                        maxlatitude=None, minlongitude=None, maxlongitude=None,
                        latitude=None, longitude=None, minradius=None,
                        maxradius=None, mindepth=None, maxdepth=None,
                        minmagnitude=None, maxmagnitude=None, magnitudetype=None,
                        eventtype=None,includeallorigins=None,
                        includeallmagnitudes=None,
                        catalog=None, contributor=None, updatedafter=None,
                       format='quakeml', 
                       workers=1):
        """
        Save seismic events from a data source to an EventBank on disk.

        This method downloads events in chunks and stores them in a structured 
        directory layout. If event IDs are known, it will fetch each event individually.
        Picks must be available from the source.

        Parameters
        ----------
        base_path : str
            Root directory to store the event files.

        path_structure : str, optional
            Template for subdirectory structure under `base_path`.
            Supports format keys like {year}, {month}, {day}, and {hour}.

        name_structure : str, optional
            Template for naming individual event files.
            Supports format keys like {event_id_end}.

        chunks : int, optional
            Number of events to fetch per iteration. Default is 100.

        max_n_events : int or None, optional
            Maximum number of events to download and save. If None, fetch all.

        eventid_tests : dict or None, optional
            Dictionary of test functions used to extract custom event IDs
            from each event object. If provided, switches fetch mode to 
            "eventid" based retrieval.

        starttime, endtime : UTCDateTime or str, optional
            Time window to filter events.

        minlatitude, maxlatitude : float, optional
            Minimum and maximum latitudes for event filtering.

        minlongitude, maxlongitude : float, optional
            Minimum and maximum longitudes for event filtering.

        latitude, longitude : float, optional
            Central coordinates for radial filtering (used with radius).

        minradius, maxradius : float, optional
            Minimum and maximum radii (in degrees) for radial filtering
            from the specified latitude/longitude.

        mindepth, maxdepth : float, optional
            Minimum and maximum depth filters in kilometers.

        minmagnitude, maxmagnitude : float, optional
            Minimum and maximum magnitude filters.

        magnitudetype : str, optional
            Type of magnitude to filter by, e.g., 'ml', 'mb', 'mw'.

        eventtype : str or list of str, optional
            Filter events by type, e.g., 'earthquake', 'quarry blast'.

        includeallorigins : bool, optional
            Whether to include all origins in event download. Defaults
            depend on picks availability mode.

        includeallmagnitudes : bool, optional
            Whether to include all magnitudes in event download.

        catalog : str, optional
            Limit to specific event catalog name (if supported by service).

        contributor : str, optional
            Limit to events from a specific contributing agency.

        updatedafter : UTCDateTime or str, optional
            Only include events updated after this time.

        format : str, optional
            File format to save events in. Default is 'quakeml'.

        workers : int, optional
            Number of threads to use when saving events in parallel
            (used only in eventid mode).

        Raises
        ------
        Exception
            If no picks service is available or pick extraction method is undefined.
        """

        # Check for available picks and determine how to fetch them
        picks_avail = self._picks_availability(eventid_tests)
        
        # Collect event filtering arguments
        ev_kwargs = {
                    k: v for k, v in locals().items()
                    if k in available_events_keys and v is not None
                        }
        
        # Raise error if picks are unavailable
        if not picks_avail["picks"]:
            raise Exception(f"No available picks service in the Client.")
        
        # natural mode refers to extract the events using the native obspy get_events function
        if picks_avail["name"] == "natural":
            ev_kwargs["includearrivals"] = True
            ev_kwargs["includeallorigins"] = includeallorigins
            ev_kwargs["includeallmagnitudes"] = includeallmagnitudes
        # This is created for cases when the full information is provided
        # only if you provide eventid information
        elif picks_avail["name"] == "eventid":
            ev_kwargs["includearrivals"] = False
            ev_kwargs["includeallorigins"] = False
            ev_kwargs["includeallmagnitudes"] = False
        
        # # Print timing information if debug is enabled
        # print(f"Event kwargs: {ev_kwargs}")
        
        # Ensure the base directory exists
        os.makedirs(base_path, exist_ok=True)
        
        # Initialize the event bank for storing events to disk
        ebank = obsplus.EventBank(
            base_path=base_path,
            path_structure=path_structure,
            name_structure=name_structure,
            format=format
        )
        
        offset_iter = 1
        iteration = 1
        total_events = 0
        while True:
            
            # Stop if maximum number of events has been reached
            if max_n_events is not None:
                remaining = max_n_events - total_events
                if remaining <= 0:
                    break
                current_chunk = min(chunks, remaining)
            else:
                current_chunk = chunks
                
            # Download event catalog
            catalog = self.get_events(orderby="time-asc", limit=current_chunk, 
                                     offset=offset_iter, **ev_kwargs)
            n_events = len(catalog)
            total_events += n_events
            
            # Prepare time window information for logging
            if n_events > 0:
                starttime = catalog[0].preferred_origin().time.strftime("%Y-%m-%d %H:%M:%S")
                endtime = catalog[-1].preferred_origin().time.strftime("%Y-%m-%d %H:%M:%S")
                
                
            tic = time.time()
            # Save events using selected mode
            if picks_avail["name"] == "natural":
                ebank.put_events(catalog)
            elif picks_avail["name"] == "eventid":
                
                ev_ids = self._get_custom_event_ids(tests=eventid_tests,**ev_kwargs)
                def save_single_event(ev_id):
                    """Fetch and save a single event to the event bank."""
                    single_event = self.get_events(eventid=ev_id, **ev_kwargs)
                    ebank.put_events(single_event)
                
                # Save chunk of events in parallel using threads
                with cf.ThreadPoolExecutor(max_workers=workers) as executor:
                    executor.map(save_single_event, ev_ids)
                    
                # for ev_id in ev_ids:
                    # save_single_event(ev_id)
                
            else:
                raise Exception("No way to extract the picks")
            
            toc = time.time()

            # Log progress
            print(
                    f"Iter {iteration:<3} | "
                    f"{n_events:>4} events | "
                    f"{starttime} → {endtime} | "
                    f"Total: {total_events:>4} | Seconds: {toc - tic:.2f}"
                )

            # Break loop if last page of results has fewer than requested
            if not catalog or len(catalog)<current_chunk:  # If no more events, break the loop
                break
            
            offset_iter += current_chunk
            iteration += 1
            
    