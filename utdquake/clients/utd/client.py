
import os
import pandas as pd
from .utils import get_event_ids, get_custom_info, save_info
from eqpy.tools.stats import get_rolling_stats
from obspy.clients.fdsn import Client as FDSNClient

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

    def get_custom_events(self, *args, max_events_in_ram=1e6, 
                          output_folder=None, drop_level=True,
                          **kwargs):
        """
        Retrieves custom seismic event data including origins, picks, 
        and magnitudes.

        Parameters:
        *args : variable length argument list
            Positional arguments passed to the get_events method.
        max_events_in_ram : int, optional, default=1e6
            Maximum number of events to hold in memory (RAM) before stopping or 
            prompting to save the data to disk.
        output_folder : str, optional, default=None
            Folder path where the event data will be saved if provided. If not 
            specified, data will only be stored in memory.
        drop_level : bool, optional, default=True
            True if you want to have only one level in your origin dataframe.
        **kwargs : variable length keyword arguments
            Keyword arguments passed to the get_events method.

        Returns:
        tuple
            A tuple containing:
            - DataFrame of origins for all events.
            - DataFrame of picks for all events.
            - DataFrame of magnitudes for all events.
        """
        # Retrieve the catalog of events using the get_events method
        catalog = self.get_events(*args, **kwargs)

        # Extract event IDs from the catalog
        ev_ids = get_event_ids(catalog)

        # Initialize lists to store origins, picks, and magnitudes
        all_origins, all_picks, all_mags = [], [], []

        # Loop through each event ID to gather detailed event information
        for ev_id in ev_ids[::-1]:
            # Catalog with arrivals. This is a workaround to retrieve 
            # arrivals by specifying the event ID.
            cat = self.get_events(eventid=ev_id)

            # Get the first event from the catalog
            event = cat[0]

            # Extract custom information for the event
            origin, picks, mags = get_custom_info(event, drop_level)

            info = {
                "origin": origin,
                "picks": picks,
                "mags": mags
            }

            # Save information to the output folder, if specified
            if output_folder is not None:
                if not os.path.isdir(output_folder):
                    os.makedirs(output_folder)
                save_info(output_folder, info=info)

            # Append information to the lists or break if memory limit is reached
            if len(all_origins) < max_events_in_ram:
                all_origins.append(origin)
                all_picks.append(picks)
                all_mags.append(mags)
            else:
                if output_folder is not None:
                    print(f"max_events_in_ram: {max_events_in_ram} is reached. "
                        "But it is still saving on disk.")
                else:
                    print(f"max_events_in_ram: {max_events_in_ram} is reached. "
                        "It is recommended to save the data on disk using the 'output_folder' parameter.")
                    break

        # Concatenate data from all events, if multiple events are found
        if len(ev_ids) > 1:
            all_origins = pd.concat(all_origins, axis=0)
            all_picks = pd.concat(all_picks, axis=0)
            all_mags = pd.concat(all_mags, axis=0)
        else:
            # If only one event is found, retain the single DataFrame
            all_origins = all_origins[0]
            all_picks = all_picks[0]
            all_mags = all_mags[0]

        return all_origins, all_picks, all_mags

    def get_stats(self, output, step, starttime, endtime, **kwargs):
        """
        Retrieve waveforms and compute rolling statistics for the specified time interval.

        Args:
            output (str): Path to the SQLite database file for saving results.
            step (int): Step size for the rolling window in seconds.
            starttime (UTCDateTime): Start time of the data.
            endtime (UTCDateTime): End time of the data.
            **kwargs: Keyword arguments for retrieving waveforms, including:
                - Additional arguments required by `self.get_waveforms`.

        Returns:
            pd.DataFrame: A DataFrame containing rolling statistics for each interval, with columns including:
            - Availability percentage
            - Gaps duration
            - Overlaps duration
            - Gaps count
            - Overlaps count
        """
        # Extract start and end times from keyword arguments
        # Retrieve waveforms using base class method
        st = self.get_waveforms(**kwargs)

        # Compute rolling statistics for the retrieved waveforms
        stats = get_rolling_stats(
            st=st,
            step=step,
            starttime=starttime.datetime,
            endtime=endtime.datetime,
            sqlite_output=output
        )

        return stats