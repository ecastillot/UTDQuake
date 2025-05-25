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
import obsplus
import warnings
import pandas as pd
from tqdm import tqdm
import concurrent.futures as cf
from obspy.clients.fdsn import Client 


warnings.filterwarnings(
    "ignore",
    message="'smi:org.gfz-potsdam.de/geofon/.*' is not a valid QuakeML URI.*",
    category=UserWarning,
    module="obspy.io.quakeml.core"
)

class Bank(Client):
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
        super().__init__(*args, **kwargs)

    def __get_custom_event_ids(self, starttime, endtime, ev_kwargs):
        """
        Retrieve custom event IDs from a catalog of seismic events.

        Parameters:
            starttime (UTCDateTime): Start time for the event search.
            endtime (UTCDateTime): End time for the event search.
            ev_kwargs (dict): Additional keyword arguments for event filtering.

        Returns:
            list: A list of custom event IDs.
        """

        keys = ["includearrivals", "includeallorigins", "includeallmagnitudes"]
        for key in keys:
            if key in ev_kwargs.keys():
                # Remove the key from ev_kwargs if it exists
                ev_kwargs[key] = False
                
        # Retrieve the catalog of events using the get_events method
        catalog = self.get_events(starttime, endtime, **ev_kwargs)

        # Initialize an empty list to store event IDs
        ev_ids = []

        # Mode to determine the format of the event ID, initialized as None
        mode = None

        # Iterate through each event in the catalog
        for event in catalog:
            
            # Extract additional data from the event
            extra_data_src = event.extra.datasource.value 
            extra_ev_id = event.extra.eventid.value

            # Define potential event ID formats
            potential_ev_ids = {
                "1": extra_data_src + extra_ev_id,
                "2": extra_ev_id
            }

            # Determine the mode (event ID format) if not already set
            if mode is None:
                for p_mode, p_ev_id in potential_ev_ids.items():
                    try:
                        # Test if the event ID exists in the catalog
                        self.get_events(starttime, endtime, eventid=p_ev_id)
                        mode = p_mode
                        break  # Exit the loop once a valid mode is found
                    except Exception:
                        pass

            # Raise an exception if no valid event ID format is found
            if mode is None:
                raise Exception(f"No event found using any of: {potential_ev_ids}")

            # Use the determined mode to select the correct event ID
            ev_id = potential_ev_ids[mode]
            ev_ids.append(ev_id)

        # Return the list of event IDs
        return ev_ids

    def load_stations(self, base_path, network=None):
        
        if network is None:
            # Load all station files from the base path
            files = glob.glob(os.path.join(base_path, "*.csv"))
        else:
            # Load station files for a specific network
            files = glob.glob(os.path.join(base_path, f"{network}.csv"))
        if not files:
            raise FileNotFoundError(f"No station files found in {base_path} for network {network}")
        
        
        
        

    def save_stations(self, base_path, workers=None, **sta_kwargs):
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

        # Run threads
        with cf.ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(process_network, networks)

        # Stop DB writer thread
        write_queue.put(None)
        writer_thread.join()
        
    def save_events(self, base_path,starttime, endtime,  
                       path_structure='{year}/{month}/{day}/{hour}',
                       name_structure='{event_id_end}',
                       chunks=100,
                       format='quakeml', 
                       debug=False,
                       workers=1,
                       **ev_kwargs):
        """
        Saves seismic event data in chunks for a specified time range.

        Parameters
        ----------
        starttime : obspy.core.utcdatetime.UTCDateTime
            Start time for querying events.
        endtime : obspy.core.utcdatetime.UTCDateTime
            End time for querying events.
        base_path : str
            Base directory where event files will be saved.
        path_structure : str, optional
            Subdirectory format for saving events. Defaults to '{year}/{month}/{day}/{hour}'.
        name_structure : str, optional
            File naming format for each event. Defaults to '{event_id_end}'.
        chunks : int, optional
            Number of events to process per batch. Defaults to 100.
        format : str, optional
            Format used to store events. Defaults to 'quakeml'.
        debug : bool, optional
            Whether to print debug information during processing. Defaults to False.
        workers : int, optional
            Number of threads to use for saving events concurrently. Defaults to 1.
        **ev_kwargs : dict
            Additional keyword arguments passed to the `get_events` method.
        """
        # Ensure the base directory exists
        os.makedirs(base_path, exist_ok=True)
        
        # Initialize the event bank for storing events to disk
        ebank = obsplus.EventBank(
            base_path=base_path,
            path_structure=path_structure,
            name_structure=name_structure,
            format=format
        )
        
        # Retrieve event IDs for the specified time range
        ev_ids = self.__get_custom_event_ids(starttime, endtime, ev_kwargs)
        
        # Process events in chunks
        for chunk in tqdm(range(0, len(ev_ids), chunks)):
            # Get the current chunk of event IDs
            ev_ids_chunk = ev_ids[chunk:chunk + chunks]
            
            # Print debug information if enabled
            if debug:
                print(f"Processing events: {ev_ids_chunk}")
            
            def save_single_event(ev_id):
                """Fetch and save a single event to the event bank."""
                catalog = self.get_events(eventid=ev_id, **ev_kwargs)
                ebank.put_events(catalog)
            
            # Save chunk of events in parallel using threads
            tic = time.time()
            with cf.ThreadPoolExecutor(max_workers=workers) as executor:
                executor.map(save_single_event, ev_ids_chunk)
            toc = time.time()

            # Print timing information if debug is enabled
            if debug:
                print(f"Saving events took: {toc - tic:.2f} seconds")
            
            # tic = time.time()
            # for ev_id in ev_ids_chunk:
            #     save_single_event(ev_id)
            # toc = time.time()
            # if debug:
            #     print(f"Time taken to retrieve events: {toc - tic:.2f} seconds")
            