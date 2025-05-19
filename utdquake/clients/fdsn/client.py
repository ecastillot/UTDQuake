
import os
import pandas as pd
from .utils import get_stations_info, get_custom_info, save_info
from utdquake.tools.stats import get_rolling_stats
from obspy.clients.fdsn import Client as FDSNClient
from obspy.core.event.event import Event
from obspy.core.event import Catalog
import concurrent.futures as cf
import time
from tqdm import tqdm
import obsplus

import warnings
warnings.filterwarnings(
    "ignore",
    message="'smi:org.gfz-potsdam.de/geofon/.*' is not a valid QuakeML URI.*",
    category=UserWarning,
    module="obspy.io.quakeml.core"
)

class Client(FDSNClient):
    """
    A client class for retrieving and calculating rolling statistics on seismic data.

    Inherits from:
        FDSNClient: Base class for FDSN web service clients.

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

    def save_chunked_events(self, starttime, endtime,  
                       base_path,
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
            
    def get_stats(self, step, network, station, location, channel, starttime, endtime, output=None, **kwargs):
        """
        Retrieve waveforms and compute rolling statistics for the specified time interval.

        Parameters:
        ----------
        step : int
            Step size for the rolling window in seconds.
        network : str
            Select one or more network codes. These can be SEED network
            codes or data center-defined codes. Multiple codes can be
            comma-separated (e.g., "IU,TA"). Wildcards are allowed.
        station : str
            Select one or more SEED station codes. Multiple codes
            can be comma-separated (e.g., "ANMO,PFO"). Wildcards are allowed.
        location : str
            Select one or more SEED location identifiers. Multiple
            identifiers can be comma-separated (e.g., "00,01"). Wildcards are allowed.
        channel : str
            Select one or more SEED channel codes. Multiple codes
            can be comma-separated (e.g., "BHZ,HHZ").
        starttime : obspy.core.utcdatetime.UTCDateTime
            Limit results to time series samples on or after the
            specified start time.
        endtime : obspy.core.utcdatetime.UTCDateTime
            Limit results to time series samples on or before the
            specified end time.
        output : str, optional
            Path to the SQLite database file for saving results. Defaults to None.
        **kwargs : dict
            Additional keyword arguments passed to the `self.get_waveforms` method.

        Returns:
        -------
        pd.DataFrame
            A DataFrame containing rolling statistics for each interval, including:
            - Availability percentage
            - Gaps duration
            - Overlaps duration
            - Gaps count
            - Overlaps count
        """
        # Retrieve waveforms using the get_waveforms method
        st = self.get_waveforms(
            network=network,
            station=station,
            location=location,
            channel=channel,
            starttime=starttime,
            endtime=endtime,
            **kwargs
        )

        # Compute rolling statistics for the retrieved waveforms
        stats = get_rolling_stats(
            st=st,
            step=step,
            starttime=starttime.datetime,
            endtime=endtime.datetime,
            sqlite_output=output
        )

        return stats