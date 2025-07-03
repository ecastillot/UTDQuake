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
import glob
import requests
import obsplus
import warnings
import pandas as pd
from tqdm import tqdm
import concurrent.futures as cf
from obspy.clients.fdsn import Client as FDSNClient 
import datetime
from obspy import UTCDateTime
from obsplus.events.get_events import _get_ids
from obspy.clients.fdsn.header import DEFAULT_PARAMETERS

warnings.filterwarnings(
    "ignore",
    message="'smi:org.gfz-potsdam.de/geofon/.*' is not a valid QuakeML URI.*",
    category=UserWarning,
    module="obspy.io.quakeml.core"
)

available_events_keys = [
    "starttime", "endtime",
    "minlatitude", "maxlatitude", "minlongitude", "maxlongitude",
    "latitude", "longitude", "minradius", "maxradius",
    "mindepth", "maxdepth",
    "minmagnitude", "maxmagnitude",
    "magnitudetype", "eventtype", 
    "catalog", "contributor", "updatedafter"]

def get_valid_event_ids(catalog, tests=None):
    """
    Get a list of valid custom event IDs from a catalog using specified tests.

    Parameters:
    - catalog: list of Event objects
    - tests: dictionary of test functions to apply (optional).

    Returns:
    - ev_ids: list of valid event IDs
    - final_tests: the reduced dictionary of tests that passed
    """
    # Initialize an empty list to collect valid custom event IDs
    ev_ids = []

    # Iterate through each event in the catalog
    for event in catalog:
        # Initialize the event ID tester with the given tests
        eit = EventIDTester(event, tests=tests)

        # Iterate through all test functions
        for test_key, test_f in eit.tests.items():
            # Generate the custom event ID using the test
            ev_id = eit.get_event_id(test_key)

            # If a valid ID is returned, save it and break the loop
            if ev_id is not None:
                ev_ids.append(ev_id)

                # Update tests to only retain the successful one for consistency
                tests = {test_key: test_f}
                break

    return ev_ids, tests

class EventIDTester:
    """
    A class to test and extract event identifiers using different functions.
    """

    def __init__(self, event, tests=None):
        """
        Initialize the EventIDTester with an event object and optional test functions.

        Parameters:
        - event: An event object containing metadata.
        - tests: A dictionary of test functions (optional).
        """
        self.event = event

        if tests is None:
            tests = self._get_default_tests()
        self.tests = tests

    def _get_default_tests(self):
        """
        Define a default dictionary of test functions to extract event IDs.

        Returns:
        - dict: A dictionary where keys are test names and values are lambda functions.
        """
        tests = {
            "f1": lambda event: event.extra.datasource.value + event.extra.eventid.value,
            "f2": lambda event: event.extra.eventid.value,
            "f3": lambda event: event.extra.datasource.value,
            "f4": lambda event: event.resource_id.id.split("/")[-1],
            "f5": lambda event: event.creation_info.agency_id + event.resource_id.id.split("/")[-1]
        }
        return tests

    def get_event_id(self, function_name):
        """
        Apply the selected test function to the event and return the extracted ID.

        Parameters:
        - function_name: The key corresponding to the desired test function.

        Returns:
        - str or None: The extracted event ID or None if the function fails.
        """
        try:
            return self.tests[function_name](self.event)
        except Exception:
            return None
    
 
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
        
    def _picks_availability(self, eventid_tests=None):
        """
        Check availability of picks and arrivals using different query modes.

        Parameters:
            eventid_tests (dict or None): Optional test cases for event ID mode.

        Returns:
            dict: Dictionary indicating which mode supports picks and arrivals.
        """
        natural_mode = self._picks_in_natural_mode()
        if natural_mode["picks"]:
            return natural_mode
        else:
            eventid_mode = self._picks_in_eventid_mode(tests=eventid_tests)
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
            
    def _picks_in_natural_mode(self):
        """
        Try to retrieve picks and arrivals using the default natural query.

        Returns:
            dict: Dictionary indicating result of the query.
        """
        info = {
            "name": "natural",
            "mode": None,
            "picks": False,
            "arrivals": False,
            "msg": None
        }

        try:
            cat = self.get_events(includearrivals=True, limit=1)
            pref_origin = cat[0].preferred_origin()

            if pref_origin:
                info["arrivals"] = True
            if cat[0].picks:
                info["picks"] = True
        except Exception:
            info["msg"] = "Client does not support get_events with include_arrivals"

        return info
    
    def _picks_in_eventid_mode(self, tests=None):
        """
        Try to retrieve picks and arrivals by querying with event IDs.

        Parameters:
            tests (dict or None): Optional test cases for generating event IDs.

        Returns:
            dict: Dictionary indicating result of the query.
        """
        info = {
            "name": "eventid",
            "mode": None,
            "picks": False,
            "arrivals": False,
            "msg": None
        }

        try:
            catalog = self.get_events(limit=1)
        except Exception:
            info["msg"] = "Client does not support get_events"
            return info

        event = catalog[0]
        eit = EventIDTester(event, tests=tests)

        for test_key in eit.tests.keys():
            ev_id = eit.get_event_id(test_key)

            if ev_id is not None:
                try:
                    cat = self.get_events(eventid=ev_id, limit=1)
                    pref_origin = cat[0].preferred_origin()

                    if pref_origin:
                        info["arrivals"] = True

                    if cat[0].picks:
                        info["picks"] = True
                        info["mode"] = test_key
                        break  # Exit loop once a valid mode is found
                except Exception:
                    pass

        return info
    
    def get_available_services(self, confirm_arrivals=True, eventid_tests=None):
        """
        Get the list of available web services, optionally confirming support for picks and arrivals.

        Parameters:
            confirm_arrivals (bool): Whether to verify support for picks and arrivals.
            eventid_tests (dict or None): Optional test cases for event ID mode.

        Returns:
            list: List of available service names.
        """
        services = list(self.services.keys())

        if confirm_arrivals:
            picks_av = self._picks_availability(eventid_tests=eventid_tests)

            if picks_av["picks"]:
                services.append("picks")
            if picks_av["arrivals"]:
                services.append("arrivals")
                
        available_services = {"available_services":services, 
                              "available_event_contributors":self.services["available_event_contributors"]}
        
        return available_services
    
    def _get_custom_event_ids(self, tests=None, **ev_kwargs):
        """
        Retrieve custom event IDs from a catalog of seismic events.

        Parameters:
            tests (dict or None): Dictionary of test functions used to generate custom event IDs.
            **ev_kwargs: Additional keyword arguments passed to the get_events method.

        Returns:
            list: A list of custom event IDs generated using provided test functions.
            final_tests: the reduced dictionary of tests that passed
        """

        # Keys that should be disabled to ensure clean event retrieval
        keys = ["includearrivals", "includeallorigins", "includeallmagnitudes"]
        for key in keys:
            if key in ev_kwargs:
                # Override specific event parameters to avoid side effects
                ev_kwargs[key] = False

        # Retrieve the event catalog with filtered parameters
        catalog = self.get_events(**ev_kwargs)

        ev_ids, tests =  get_valid_event_ids(catalog=catalog,tests=tests)

        # Return the list of valid custom event IDs
        return ev_ids, tests

    def save_stations_to_bank(self, base_path, workers=None, **sta_kwargs):
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
                        print(f"DB write error: {e}")
                        traceback.print_exc()
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
                    msg = f"Error processing network {network_code}: {e}"
                    traceback.print_exc()
                    break  # unexpected error, stop retrying

            with lock:
                completed += 1
                print(f"Progress: {completed}/{total_networks}, {msg}")
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
            
    