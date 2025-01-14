
import os
import pandas as pd
from .utils import get_event_ids, get_custom_info, save_info
from utdquake.tools.stats import get_rolling_stats
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

    def get_custom_events(self, starttime, endtime, max_events_in_ram=1e6,
                      output_folder=None, drop_level=True, **kwargs):
        """
        Retrieves custom seismic event data, including origins, picks, and magnitudes.

        Parameters:
        ----------
        starttime : obspy.core.utcdatetime.UTCDateTime
            Limit results to time series samples on or after the specified start time.
        endtime : obspy.core.utcdatetime.UTCDateTime
            Limit results to time series samples on or before the specified end time.
        max_events_in_ram : int, optional, default=1e6
            Maximum number of events to hold in memory (RAM) before stopping or 
            prompting to save the data to disk.
        output_folder : str, optional, default=None
            Folder path where the event data will be saved if provided. If not 
            specified, data will only be stored in memory.
        drop_level : bool, optional, default=True
            If True, the origin DataFrame will have only one hierarchical level.
        **kwargs : variable length keyword arguments
            Additional arguments passed to the `get_events` method.

        Returns:
        -------
        tuple
            A tuple containing:
            - pd.DataFrame: Origins for all events.
            - pd.DataFrame: Picks for all events.
            - pd.DataFrame: Magnitudes for all events.
        """
        # Retrieve the catalog of events using the get_events method
        catalog = self.get_events(starttime, endtime,
                                  **kwargs)

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