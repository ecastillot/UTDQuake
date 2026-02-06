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
import datetime
from typing import  Optional
import os
import sqlite3
import time
import obsplus
import warnings
import pandas as pd
from obspy import UTCDateTime
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

def generate_agency_availability_report(
    starttime: UTCDateTime,
    endtime: UTCDateTime,
    chunk_seconds: int = 3600,
    patience: int = 10,
    debug: bool = False,
    output: Optional[str] = None,
    additional_mappings: Optional[dict] = None,
    ):
    """
    Generate a report of FDSN agency capabilities, including picks and arrivals.

    Parameters
    ----------
    starttime : UTCDateTime
        Start time of the query window.
    endtime : UTCDateTime
        End time of the query window.
    chunk_seconds : int, optional
        Duration of each time chunk (in seconds). Default is 3600.
    patience : int, optional
        Number of chunks to try before giving up. Default is 10.
    output : str or None, optional
        Path to output CSV file. If None, result is returned but not saved.
    additional_mappings : dict or None, optional
        Additional FDSN URL mappings to use.

    Returns
    -------
    pd.DataFrame
        DataFrame containing agency capabilities and pick information.
    """
    agency_info_template = {
        "agency": None,
        "starttime": starttime,
        "endtime": endtime,
        "url": None,
        "dataselect": False,
        "station": False,
        "event": False,
        "picks": False,
        "arrivals": False,
        "picks_method_name": None,
        "picks_method_mode": None,
    }

    # Merge additional mappings if provided
    url_mappings = fut.extend_fdsn_url_mappings(additional_mappings or {}).copy()

    info = []

    for key in sorted(url_mappings.keys()):
        agency_info = agency_info_template.copy()
        agency_info["agency"] = key
        agency_info["url"] = url_mappings[key]

        logger.info(f"Checking agency: {key} at {agency_info['url']}")

        try:
            client = Client(key)
        except Exception as e:
            logger.error(f"Error creating client for {key}: {e}")
            continue

        # Check which FDSN services are supported
        services = list(client.services.keys())
        for service in services:
            if service in agency_info:
                agency_info[service] = True

        # Try to retrieve picks and arrivals
        try:
            picks_service = client.picks_service(
                starttime=starttime,
                endtime=endtime,
                chunk_seconds=chunk_seconds,
                patience=patience,
            )

            agency_info["picks"] = picks_service["picks"]
            agency_info["arrivals"] = picks_service["arrivals"]
            agency_info["picks_method_name"] = picks_service["name"]
            agency_info["picks_method_mode"] = picks_service["mode"]

        except Exception as e:
            logger.error(f"Error getting picks service for {key}: {e}")

        logger.debug(f"Agency {key} info: {agency_info}")

        info.append(agency_info)

    df = pd.DataFrame(info)

    if output:
        df.to_csv(output, index=False)
        logger.info(f"Saved agency report to {output}")

    return df

class Client(FDSNClient):

    def __init__(self,*args, **kwargs):
        """
        Initialize the Client class with logging configuration and base setup.

        This constructor extends the standard FDSNClient by optionally enabling
        logging configuration. Additional arguments are passed to the base class.

        Parameters
        ----------
        *args : tuple
            Positional arguments to be passed to the base FDSNClient constructor.
        **kwargs : dict
            Keyword arguments to be passed to the base FDSNClient constructor.
        """

        self.event_id_query_fmt = None

        super().__init__(*args,**kwargs)
        
    def _picks_availability(self, starttime, endtime, eventid_tests=None, **ev_kwargs):
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
        logger.info(f"Checking picks availability for {self.base_url} from {starttime} to {endtime}")
        natural_mode = self._picks_in_natural_mode(starttime, endtime,**ev_kwargs)

        if natural_mode["picks"]:
            logger.info(f"Found picks in natural mode (using includearrivals=True) for {self.base_url}")
            return natural_mode
        else:
            logger.info(f"No picks found in natural mode (using includearrivals=True) for {self.base_url}, trying event ID mode")
            eventid_mode = self._picks_in_eventid_mode(starttime, endtime,tests=eventid_tests,**ev_kwargs)
            if eventid_mode["picks"]:
                logger.info(f"Found picks in event ID mode for {self.base_url} using {eventid_mode['mode']} strategy. Check DEFAULT strategies in fdsn.utils.EventIDTester")
                return eventid_mode
            else:
                logger.warning(f"No picks found in either mode for {self.base_url} from {starttime} to {endtime}")
                return {
                    "name": None,
                    "mode": None,
                    "picks": False,
                    "arrivals": False,
                    "msg": None
                }
            
    def _picks_in_natural_mode(self,starttime, endtime,**ev_kwargs):
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
            if "includearrivals" in ev_kwargs:
                # Remove includearrivals from kwargs to avoid conflicts
                ev_kwargs.pop("includearrivals")

            # Query event catalog including arrivals
            cat = self.get_events(starttime=starttime,
                                    endtime=endtime,
                                    includearrivals=True,**ev_kwargs)
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
    
    def _picks_in_eventid_mode(self,starttime, endtime, tests=None,**ev_kwargs):
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
                                    endtime=endtime,**ev_kwargs)
        except Exception as e:
            info["msg"] = "Client does not support get_events"
            logger.error(f"Failed to retrieve events: {e}")
            return info

        # Select the first event as a reference to generate event IDs
        event = catalog[0]
        logger.debug(f"Using event {event.resource_id} as reference for event ID generation.")
        eit = fut.EventIDTester(event, tests=tests)
        logger.debug(f"EventIDTester initialized with {len(eit.tests)} test strategies.")

        # Iterate over all test keys to try multiple event ID generation strategies
        for test_key in eit.tests.keys():
            logger.debug(f"Testing event ID generation with key: {test_key}")
            ev_id = eit.get_event_id(test_key)
            if ev_id is not None:
                logger.debug(f"Generated event ID: {ev_id} using key: {test_key}")
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
                    logger.error(f"Failed to retrieve events for event ID: {ev_id} using key: {test_key}")
                    # Ignore failure and continue testing other strategies
                    pass
            else:
                logger.debug(f"Event ID generation failed for key: {test_key}")

        return info
    
    def _get_reference_event_time(self, starttime, endtime, 
                                    chunk_seconds=3600,
                                    patience: int = 10,
                                    reverse=False,
                                    **ev_kwargs):
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
        generator_dict = fut.catalog_generator(self, starttime=starttime, endtime=endtime,
                                    chunk_seconds=chunk_seconds,patience=patience,
                                    reverse=reverse,**ev_kwargs)
        origin_time = None

        # Iterate through each catalog chunk
        for generator in generator_dict:
            catalog = generator["catalog"]
            if len(catalog) > 0:
                # If at least one event is present, get the origin time of the first
                event = catalog[0]
                origin_time = event.preferred_origin().time
                break

        return origin_time

    def picks_service(self, starttime, endtime, 
                        chunk_seconds=3600,
                        patience: int = 10,
                        eventid_tests=None,
                        reverse=False,
                        **ev_kwargs):
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
                                                            patience=patience,
                                                            reverse=reverse,
                                                            **ev_kwargs)
            # Raise an error if no events were found
            if ref_event_time is None:
                raise Exception("No events found in the specified time range.")

            # Check pick availability within ±60 seconds of the reference event
            picks_avail = self._picks_availability( starttime=ref_event_time - 60,
                                                    endtime=ref_event_time + 60,
                                                    eventid_tests=eventid_tests,**ev_kwargs)
            return picks_avail
        else:
            raise Exception("The client does not support the 'event' service.")

    @staticmethod
    def save_inventory_to_bank(stations_bank_path, inventory):
        """
        Saves each network from an ObsPy Inventory to a StationXML file and
        inserts its metadata into a shared SQLite database.

        Parameters
        ----------
        stations_bank_path : str
            Path to the folder where files and database will be stored.
        inventory : obspy.Inventory
            The Inventory object containing network/station metadata.
        """
        os.makedirs(stations_bank_path, exist_ok=True)
        db_path = os.path.join(stations_bank_path, ".stations.db")

        if not os.path.exists(db_path):
            logger.info(f"Creating new SQLite DB at {db_path}")


        try:
            with sqlite3.connect(db_path) as conn:
                for net in inventory.networks:
                    try:
                        net_code = net.code
                        # Create a new Inventory with just this network
                        single_inv = inventory.select(network=net_code)
                        
                        # Save StationXML
                        xml_path = os.path.join(stations_bank_path, f"{net_code}.xml")
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

    def download_stations(self, stations_bank_path, 
                            workers=None, **sta_kwargs):
        """
        Saves station data to a specified base path using parallel threads.

        Parameters
        ----------
        stations_bank_path : str
            Base directory where station files will be saved.
        workers : int or None, optional
            Number of worker threads to use. If None, the default from ThreadPoolExecutor is used.
        **sta_kwargs : dict
            Additional keyword arguments passed to the `get_stations` method.
        """
        logger.info(f"Saving stations to bank at {stations_bank_path} and sta_kwargs={sta_kwargs}")

        # Get the list of supported services from the client
        services = list(self.services.keys())
        if "station" not in services:
            raise Exception("The client does not support the 'station' service.")


        # Ensure the base directory exists
        os.makedirs(stations_bank_path, exist_ok=True)
        

        # Default to response level if not specified
        if "level" not in sta_kwargs:
            sta_kwargs["level"] = "channel"
        
        # Fetch network-level metadata
        kwargs = sta_kwargs.copy()
        kwargs["level"] = "network"
        net_inv = self.get_stations(**kwargs)
        networks = sorted(set(net.code for net in net_inv))
        
        del net_inv, kwargs

        if workers is None:
            cpu_cores = os.cpu_count() or 1  # fallback to 1 if cpu_count() returns None
            workers = min(workers, cpu_cores)  # max 4 workers or number of cores, whichever is smaller
            if len(networks) <= workers:
                workers = len(networks)  # Use one thread per network if fewer networks than workers
            
            logger.info(f"Using {workers} worker threads for saving stations.")


        # SQLite DB path
        db_path = os.path.join(stations_bank_path, ".stations.db")

        # Queue for thread-safe database writing
        write_queue = queue.Queue()

        total_networks = len(networks)
        completed = 0
        lock = threading.Lock()  # to safely update the counter

        def db_writer():
            """Dedicated DB writer thread with INSERT OR REPLACE to avoid duplicates."""
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                while True:
                    df = write_queue.get()
                    if df is None:
                        break
                    try:
                        columns = list(df.columns)
                        colnames = ", ".join(columns)
                        placeholders = ", ".join(["?"] * len(columns))
                        insert_stmt = f"""
                            INSERT OR REPLACE INTO stations_index ({colnames})
                            VALUES ({placeholders})
                        """

                        for _, row in df.iterrows():

                            values = tuple()
                            for col in columns:
                                if isinstance(row[col], pd.Timestamp) and not pd.isna(row[col]):
                                    row[col] = row[col].isoformat(sep=' ')
                                elif pd.isna(row[col]):
                                    row[col] = None  # Convert NaT to None for SQLite compatibility 
                                elif isinstance(row[col], str):
                                    if col == "location":
                                        row[col] = row[col].zfill(2).strip()  # Ensure location codes are
                                    else:
                                        row[col] = row[col].strip()
                                elif isinstance(row[col], (int, float)):
                                    row[col] = float(row[col])  # Ensure numeric types are float
                                else:
                                    row[col] = str(row[col])  # Convert other types to string
                                values += (row[col],)

                            try:
                                cursor.execute(insert_stmt, values)
                            except Exception as e:
                                logger.warning(f"Failed to insert row: {row.to_dict()} - {e}")
                        conn.commit()

                    except Exception as e:
                        logger.exception(f"DB write error: {e}")
                    finally:
                        write_queue.task_done()

        fut.initialize_stations_db(db_path)
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
                    xml_path = os.path.join(stations_bank_path, f"{network_code}.xml")
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

        
        # Run threads
        with cf.ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(process_network, networks)

        # Stop DB writer thread
        write_queue.put(None)
        writer_thread.join()

    def download_events(self, events_bank_path,
                        starttime, endtime, 
                        path_structure='{year}/{month}/{day}/{hour}',
                        name_structure='{event_id_end}',
                        stations_bank_path=None,
                        calculate_d_az = False,
                        max_n_events=None,
                        max_from_bank=False,
                        chunk_seconds=7200,
                        patience=10,
                        eventid_tests=None,
                        reverse=False,
                        minlatitude=None,
                        maxlatitude=None, minlongitude=None, maxlongitude=None,
                        latitude=None, longitude=None, minradius=None,
                        maxradius=None, mindepth=None, maxdepth=None,
                        minmagnitude=None, maxmagnitude=None, magnitudetype=None,
                        eventtype=None, includeallorigins=None,
                        includeallmagnitudes=None,
                        catalog=None, contributor=None, updatedafter=None,
                        format='quakeml', 
                        workers=4):
        """
        Save seismic events from a data source to an EventBank on disk.

        Downloads events in chunks and stores them in a structured directory layout.
        Can use either natural mode or eventid-based mode depending on the availability
        of picks.

        Parameters
        ----------
        events_bank_path : str
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

        """
        
        logger.info(f"{'#'*20} PREPARING TO DOWNLOAD EVENTS ")
        logger.info(f"Saving events from {starttime} to {endtime} in {events_bank_path}")
        # Check for available picks
        logger.info(f"Checking picks availability from {starttime} to {endtime}...")

        ev_kwargs = {"latitude": latitude, "longitude": longitude,
                     "minradius": minradius, "maxradius": maxradius,
                     "minlatitude": minlatitude, "maxlatitude": maxlatitude,
                     "minlongitude": minlongitude, "maxlongitude": maxlongitude,
                     "mindepth": mindepth, "maxdepth": maxdepth,
                     "minmagnitude": minmagnitude, "maxmagnitude": maxmagnitude,
                     "magnitudetype": magnitudetype, "eventtype": eventtype,
                     "catalog": catalog,
                     "contributor": contributor, "updatedafter": updatedafter}
        
        picks_avail = self.picks_service(
                                        starttime=starttime, endtime=endtime,
                                        chunk_seconds=chunk_seconds, patience=patience,
                                        eventid_tests=eventid_tests,reverse=reverse, **ev_kwargs)
        if stations_bank_path is not None:
            stations_db_path = os.path.join(stations_bank_path, ".stations.db")

        if not picks_avail["picks"]:
            raise Exception(f"No available picks service in the Client. Picks = {picks_avail}")

        if calculate_d_az and stations_bank_path is None:
            raise Exception("If calculate_d_az is True, stations_bank_path must be provided.")
        elif calculate_d_az and not os.path.exists(stations_bank_path):
            raise Exception(f"Stations bank path {stations_bank_path} does not exist.")
        elif calculate_d_az is None and stations_bank_path is not None:
            logger.debug("calculate_d_az is None, but stations_bank_path is provided. "
                         "This will not be used. Set calculate_d_az=True to use it.")
        elif calculate_d_az and os.path.exists(stations_bank_path):
            stations_db_path = os.path.join(stations_bank_path, ".stations.db")
            stations = fut.load_stations_metadata_from_bank(db_path=stations_db_path)
        else:
            stations = None



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

        os.makedirs(events_bank_path, exist_ok=True)


        ## initialize the event bank
        ebank = obsplus.EventBank(
            base_path=events_bank_path,
            path_structure=path_structure,
            name_structure=name_structure,
            format=format
        )
        ebank_index_path = os.path.join(events_bank_path, ".index.db")
        

        logger.info(f"Saving events to {events_bank_path} with structure: {path_structure}")

        # Getting the total number of events in the event bank
        # if max_from_bank is True, we will read the event bank index
        if max_from_bank:
            new_time, total_events = fut.update_time_from_bank(
                ebank=ebank,
                starttime=starttime,
                endtime=endtime,
                max_n_events=max_n_events,
                reverse=reverse
            )
            if new_time is None:
                logger.warning(f"Skipping download: no new events in range.")
                return

            if reverse:
                endtime = new_time
            else:
                starttime = new_time
        else:
            total_events = 0

        iteration = 0
        id_tests = eventid_tests

        logger.info(f"{'#'*20} EVENT DOWNLOADING")
        logger.info(f"Starting event download from from {starttime} to {endtime} (reverse={reverse})")
        error_patience_counter = 0
        for catalog_dict in fut.catalog_generator(self, starttime=starttime, endtime=endtime,
                                 chunk_seconds=chunk_seconds,
                                 patience=patience,reverse=reverse, **ev_kwargs):
            # print("This function is under development. Please check back later.")
            
            if error_patience_counter >= patience:
                logger.error(f"Error patience counter reached {error_patience_counter}. Stopping download.")
                break

            catalog = catalog_dict["catalog"]
            original_len_catalog = len(catalog)
            chunk_starttime = catalog_dict["starttime"].strftime("%Y-%m-%d %H:%M:%S.%f")
            chunk_endtime = catalog_dict["endtime"].strftime("%Y-%m-%d %H:%M:%S.%f")
            chunk_creation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            logger.info(f"Chunk id: {iteration:<3} initiated | "
                        f"Time range: {chunk_starttime} - {chunk_endtime} | "
                        f"Chunk creation time: {chunk_creation_time}")

            if len(catalog) == 0:
                error_patience_counter += 1
                logger.warning(f"Chunk id {iteration:<3} has no events. "
                               f"Start time: {chunk_starttime}, End time: {chunk_endtime}. "
                               f"Error patience counter: {error_patience_counter}. "
                               f"Continuing to next chunk.")
                continue

            # Trim if over the event limit
            if max_n_events is not None:
                logger.debug(f"Checking if total events {total_events} exceed max_n_events {max_n_events}")
                remaining = max_n_events - total_events
                if remaining <= 0:
                    logger.info(f"Reached max_n_events limit of {max_n_events}. Stopping download.")
                    break
                elif remaining < len(catalog):
                    catalog.events = catalog.events[:remaining]
                    logger.debug(f"Trimming catalog to {len(catalog)} events (remaining: {remaining})")

            logger.info(f"Chunk id: {iteration:<3} - Initial fast query without requering picks. "
                        f"Apparently {len(catalog):>4} events")

                    
            if stations is not None:
                logger.info(f"Using stations from {stations_bank_path} to recalculate distances and azimuths")

            tic = time.time()


            if picks_avail["name"] == "natural":
                if stations is not None:
                    # Append stations metadata to the catalog
                    catalog = fut.append_stations_to_catalog(catalog=catalog, 
                                                            df_stations=stations,
                                                            calculate_d_az=calculate_d_az,
                                                            ebank_index_path=ebank_index_path,
                                                                        )
                    if len(catalog) == 0:
                        logger.error(f"Failed to save events in chunk id {iteration:<3}. No events after appending stations metadata.")
                        error_patience_counter += 1
                        logger.warning(
                                    f"Error Patience counter [{error_patience_counter}/{patience}]. "
                                    f"Chunk id {iteration:<3} has no acceptable events. "
                                    f"Start time: {chunk_starttime}, End time: {chunk_endtime}. "
                                    f"Continuing to next chunk.")
                        continue

            elif picks_avail["name"] == "eventid":
                ev_ids, id_tests =  fut.get_valid_event_ids(catalog=catalog,tests=id_tests)

                events_from_evid = []
                def save_single_event(ev_id):
                    single_catalog = self.get_events(eventid=ev_id, **ev_kwargs)

                    if stations is not None:
                        # Append stations metadata to the single event catalog
                        single_catalog = fut.append_stations_to_catalog(
                                                                catalog=single_catalog, 
                                                                df_stations=stations,
                                                                calculate_d_az=calculate_d_az,
                                                                ebank_index_path=ebank_index_path,
                                                            )
                        
                    
                    if len(single_catalog) == 0:
                        logger.error(f"Failed to save event {ev_id} in chunk id {iteration:<3}. No events after appending stations metadata.")
                    else:
                        events_from_evid.append(single_catalog[0])
                

                if workers > len(ev_ids):
                    workers = len(ev_ids)  # Use one thread per event if fewer events than workers
                    logger.info(f"Using {workers} worker threads for saving events.")
                
                if workers == 1:
                    for ev_id in ev_ids:
                        save_single_event(ev_id)
                else:
                    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
                        executor.map(save_single_event, ev_ids)

                catalog.events = events_from_evid
                if len(catalog) == 0:
                    logger.error(f"Failed to save events in chunk id {iteration:<3}. No events after appending stations metadata.")
                    error_patience_counter += 1
                    logger.warning(
                                    f"Error Patience counter [{error_patience_counter}/{patience}]. "
                                    f"Chunk id {iteration:<3} has no acceptable events. "
                                    f"Start time: {chunk_starttime}, End time: {chunk_endtime}. "
                                    f"Continuing to next chunk.")
                    continue

            else:
                raise Exception("No way to extract the picks")



            new_len_catalog = len(catalog)

            ### putting events
            try:
                ebank.put_events(catalog)
                logger.info(f"Saved {new_len_catalog} events of {original_len_catalog} possible in chunk id {iteration:<3} "
                            f"from {chunk_starttime} to {chunk_endtime} in {events_bank_path}")
            except Exception as e:
                error_patience_counter += 1
                logger.error(f"Failed to save events: {e}. "
                            )
                logger.warning(
                                    f"Error Patience counter [{error_patience_counter}/{patience}]. "
                                    f"Chunk id {iteration:<3} has no acceptable events. "
                                    f"Start time: {chunk_starttime}, End time: {chunk_endtime}. "
                                    f"Continuing to next chunk.")
                continue


            logger.info(f"Creating stations summary based on the events in the event bank at {events_bank_path}/.stations")
            stations_folder = os.path.join( events_bank_path,".stations")
            summary = fut.get_stations_summary(stations_folder=stations_folder)
            if summary is not None:
                logger.info(f"Updating stations summary in the event bank at {events_bank_path}")
                with sqlite3.connect(ebank_index_path) as ev_con:
                    summary.to_sql(
                                    "/stations/index", ev_con, 
                                    if_exists='append', index=False
                                )
                    
                    now = datetime.datetime.now().timestamp()

                    # put it in a dataframe
                    df = pd.DataFrame({"last_updated": [now]})
                    df.to_sql(
                            "/stations/last_updated", ev_con,
                            if_exists="replace", index=False
                        )
                logger.info(f"Stations summary updated successfully.")
                    # summary["creation_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            # Trying to double check if they are well saved
            # we will check if the value in time column are the same in both dataframes
            catalog_df = catalog.to_df()
            ebank_df = ebank.read_index()
            if not catalog_df.empty and not ebank_df.empty:
                if "time" in catalog_df.columns and "time" in ebank_df.columns:
                    catalog_df['in_ebank'] = catalog_df['time'].isin(ebank_df['time'])
                    if not catalog_df['in_ebank'].all():
                        logger.warning(f"{len(catalog)} events in the catalog were NOT saved properly in the event bank.")

                        # Show what events are missing
                        missing_events = catalog_df[~catalog_df['in_ebank']]
                        ev_ids_and_time_tuple = list(zip(missing_events['event_id'], missing_events['time']))
                        logger.warning(f"Missing events: {len(missing_events)}")
                    else:
                        logger.info("All events in the catalog were saved properly in the event bank.")
                else:
                    logger.warning("Time column is missing in either catalog or event bank DataFrame.")

            toc = time.time()

            n_events = len(catalog)
            total_events += n_events
            
            logger.info(
                f"Chunk id: {iteration:<3} concluded | "
                f"Start time: {chunk_starttime}, End time: {chunk_endtime} | "
                f"({n_events:>4} events in {toc - tic:.2f} s) | "
                f"Total: {total_events:>4}/{max_n_events} |"
                f"Bank : {events_bank_path}"
            )
            error_patience_counter = 0  # Reset error patience counter after successful chunk
            logger.info(f"Reset error patience counter to 0 after successful chunk if {iteration}")
            iteration += 1
            if max_n_events is not None and total_events >= max_n_events:
                break

        
