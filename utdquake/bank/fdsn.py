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

class EventIDTester():
    def __init__(self,event,tests=None):
        self.event = event
        
        if tests is None:
            tests = self._get_default_tests()
        self.tests = tests
        
    def _get_default_tests(self):
        tests = {
                "f1": lambda event: event.extra.datasource.value + event.extra.eventid.value,    
                "f2": lambda event: event.extra.eventid.value,    
                "f3": lambda event: event.extra.datasource.value,    
                "f4": lambda event: event.resource_id.id.split("/")[-1],    
                "f5": lambda event: event.creation_info.agency_id + event.resource_id.id.split("/")[-1]   
                }
        return tests
    
    def get_event_id(self,function_name):
        try:
            return self.tests[function_name](self.event)
        except:
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
        
    def _picks_availability(self):
        natural_mode = self._picks_in_natural_mode()
        if natural_mode["picks"]:
            return natural_mode
        else:
            eventid_mode = self._picks_in_eventid_mode()
            if eventid_mode["picks"]:
                return eventid_mode
            else:
                return {"name":None,"mode":None,"picks": False, "arrivals":False, "msg":None}
            
    def _picks_in_natural_mode(self):
        
        info = {"name":"natural","mode":None,"picks": False, "arrivals":False, "msg":None}
        
        try:
            cat = self.get_events(includearrivals=True, limit=1)
            
            pref_origin = cat[0].preferred_origin()
                    
            if pref_origin:
                info["arrivals"] = True
            
            if cat[0].picks:
                info["picks"] = True

        except:
            info["msg"] = "Client does not support get_events with include_arrivals"
        
        return info
    
    def _picks_in_eventid_mode(self,tests=None):
        
        info = {"name":"eventid","mode":None,"picks": False, "arrivals":False, "msg":None}
        
        try:
            catalog = self.get_events(limit=1)
        except:
            info["msg"] = "Client does not support get_events"
            return info
        
        event = catalog[0]
        
        eit = EventIDTester(event, tests=tests)
        
        
        for test_key in eit.tests.keys():
            ev_id = eit.get_event_id(test_key)
            
            if ev_id is not None:
                try:
                    # Test if the event ID exists in the catalog
                    cat = self.get_events(eventid=ev_id, limit=1)
                    
                    pref_origin = cat[0].preferred_origin()
                    
                    if pref_origin:
                        info["arrivals"] = True
                        
                    if cat[0].picks:
                        info["picks"] = True
                        info["mode"] = test_key
                        break  # Exit the loop once a valid mode is found
                except Exception:
                    pass
                
        return info    
    
    def get_available_services(self, confirm_arrivals=True):
        services = list(self.services.keys())
        
        if confirm_arrivals:
            
            picks_av = self._picks_availability()
            
            services += ["picks"] if picks_av["picks"] else []
            services += ["arrivals"] if picks_av["arrivals"] else []
            
            # if picks_av["availability"]:
                
            
            # cat = self.get_events(limit=1,includearrivals=True,
            #                       eventid=0)
            # print(cat[0].resource_id )
            # # print(cat[0].picks)
            # # print(cat[0].preferred_origin().arrivals)
            # exit()
            # preferred_origin = cat[0].preferred_origin()
            # try :
            #     cat = self.get_events(limit=1)
            #     preferred_origin = cat[0].preferred_origin()
            #     starttime = preferred_origin.time - datetime.timedelta(seconds=1)
            #     endtime = preferred_origin.time + datetime.timedelta(seconds=1)
            #     min_latitude = preferred_origin.latitude - 0.1
            #     max_latitude = preferred_origin.latitude + 0.1
            #     min_longitude = preferred_origin.longitude - 0.1
            #     max_longitude = preferred_origin.longitude + 0.1
                
            #     ## We need to provide id per event to get picks and arrivals. This is funny (potential issue to obspy?).
            #     ## If we do not provide id, it will return the event but without picks and arrivals.
            #     ## this function extracts the event id from the catalog and then retrieves the event with that id.
            #     ev_ids = self.__get_custom_event_ids(
            #                                 starttime=starttime,
            #                                 endtime=endtime,
            #                                 ev_kwargs={
            #                                     "minlatitude": min_latitude,
            #                                     "maxlatitude": max_latitude,
            #                                     "minlongitude": min_longitude,
            #                                     "maxlongitude": max_longitude,
            #                                 })
            #     new_cat = self.get_events(
            #                             eventid= ev_ids[0])
                
            #     picks = True if new_cat[0].picks else False
            #     arrivals = True if new_cat[0].preferred_origin().arrivals else False
            #     services += ["picks"] if picks else []
            #     services += ["arrivals"] if arrivals else []
            # except Exception as e:
            #     print(f"Error confirming arrivals: {e}")
            #     # If there's an error, we just return the available services without arrivals
            #     pass
        return services
    
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

        # # Mode to determine the format of the event ID, initialized as None
        # mode = None

        # Iterate through each event in the catalog
        for event in catalog:
            
            if "extra" in event.keys():
                # Extract  data from the event
                extra_data_src = event.extra.datasource.value 
                extra_ev_id = event.extra.eventid.value

                # Define potential event ID formats
                potential_ev_ids = {
                    "e1": extra_data_src + extra_ev_id,
                    "e2": extra_ev_id
                }
            else:
                # If no extra data is available, use the event ID directly
                potential_ev_ids = {
                    "1": event.resource_id.id,
                    "2": event.resource_id.id.split("eventid=")[-1].split("&")[0],
                    "3": event.resource_id.id.split("/")[-1],
                    "4": event.creation_info.agency_id + event.resource_id.id.split("/")[-1]
                }
                

            # Determine the mode (event ID format) if not already set
            if self.event_id_query_fmt is None:
                for p_mode, p_ev_id in potential_ev_ids.items():
                    try:
                        # Test if the event ID exists in the catalog
                        cat=self.get_events(starttime, endtime, eventid=p_ev_id)
                        self.event_id_query_fmt = p_mode
                        break  # Exit the loop once a valid mode is found
                    except Exception:
                        pass
            # Raise an exception if no valid event ID format is found
            if self.event_id_query_fmt:
                raise Exception(f"No event found using any of: {potential_ev_ids}")

            # Use the determined mode to select the correct event ID
            ev_id = potential_ev_ids[self.event_id_query_fmt]
            ev_ids.append(ev_id)

        # Return the list of event IDs
        return ev_ids

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
        
    def save_events_to_bank(self, base_path,starttime, endtime,  
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
            