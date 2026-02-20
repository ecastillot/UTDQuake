import os
import pandas as pd
import numpy as np
import sqlite3
from typing import  Optional

from .qc import apply_utdq_qc
from ..core.config import KM_PER_DEG
from ..writers.parquet import to_parquet

from obsplus import EventBank as ObsplusEventBank
from obspy import Catalog


def utdq_picks_to_df(self,phase=None):
    """
    Merge arrivals, picks, and event metadata into a single DataFrame.

    This method combines arrival information with corresponding pick times
    and event metadata. It also computes the hypocentral distance for each
    pick using horizontal distance (in degrees) and event depth.

    The hypocentral distance is computed assuming a spherical Earth
    approximation using the global configuration parameter
    ``config.KM_PER_DEG`` (default: 111.19 km/deg). Users may modify this
    value before calling this method, e.g.:

        >>> import utdquake.config
        >>> utdquake.config.KM_PER_DEG = 110.57

    Returns
    -------
    pandas.DataFrame
        DataFrame containing merged pick, arrival, and event information.
        Includes computed columns:
        - ``linear_hyp_distance``: hypocentral distance in kilometers
        - ``travel_time``: travel time in seconds.
    """
    events = self.utdq_events_to_df()
    arrivals = self.arrivals_to_df()
    picks = self.picks_to_df()

    # Keep only relevant pick information
    picks = picks[['resource_id','time','evaluation_mode']]
    picks.rename(columns={'resource_id': 'pick_id'}, inplace=True)

    # Merge arrivals with pick times
    df = pd.merge(
        arrivals,
        picks,
        on = 'pick_id',
        how='left'
    )

    # Attach event metadata including depth
    df = pd.merge(
        df,
        events[['event_id','preferred_origin_id',"depth"]],
        left_on = 'origin_id',
        right_on = 'preferred_origin_id',
        how = 'left'
    )

    # Compute hypocentral distance (km)
    df["linear_hyp_distance"] = np.sqrt(
                                (df["distance"] * KM_PER_DEG) ** 2 +
                                (df["depth"]/1e3) ** 2
                                )
    df["travel_time"] = (df["time"] - df["origin_time"]).dt.total_seconds()
    
    if phase is None:
        phase = ["P","S","Pn","Sn","Pg","Sg",
                 "p","s","pn","sn","pg","sg",
                 "PN","SN","PG","SG",]
        

    if isinstance(phase, str):
        phase = [phase]
        
    df = df[df["phase"].isin(phase)].reset_index(drop=True)


    # Clean up final DataFrame
    df.drop_duplicates(subset=['resource_id','pick_id'], inplace=True)
    df.drop(columns=['depth'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.sort_values(by='time', inplace=True,ignore_index=True)
    return df


def utdq_events_to_df(self):
    """
    Convert an ObsPy Catalog to a DataFrame with preferred origin mapping.

    Extracts event-level metadata from the ObsPy Catalog and determines
    the preferred origin ID for each event. If an event does not have an
    explicitly defined preferred origin, the first available origin is used.

    Parameters
    ----------
    self : obspy.core.event.Catalog
        ObsPy Catalog object containing seismic events.

    Returns
    -------
    pandas.DataFrame
        DataFrame representation of the catalog with an additional column
        ``preferred_origin_id`` indicating the resource ID of each event's
        preferred (or fallback) origin.
    """

    events = self.to_df()
    preferred_origins = {}
    for event in self:
        # Determine preferred origin or fallback to first available origin
        event_id = str(event.resource_id)

        # Preferred origin (may be None)
        origin = event.preferred_origin() or (event.origins[0] if event.origins else None)

        if origin is None:
            origin_id = None
        else:
            origin_id = str(origin.resource_id)

        preferred_origins[event_id] = origin_id

    #append origin metadata
    events['preferred_origin_id'] = events['event_id'].map(preferred_origins)

    events.drop_duplicates(subset='event_id', inplace=True,
                           ignore_index=True)

    return events


def utdquake_obspy_patch():
    """
    Patch ObsPy's :class:`obspy.core.event.Catalog` with UTDQuake helper methods.

    This function dynamically attaches the following methods to
    :class:`obspy.core.event.Catalog`:

    - ``utdq_picks_to_df``: Merge arrivals, picks, and event metadata into a DataFrame.
    - ``utdq_events_to_df``: Convert catalog events to a DataFrame with preferred origin mapping.
    - ``apply_utdq_qc``: Apply UTDQuake pick-level and event-level QC to the catalog.

    After calling this function, any ObsPy :class:`Catalog` instance will have
    direct access to these UTDQuake methods, for example:

        >>> import utdquake
        >>> from obspy import read_events
        >>> cat = read_events("some_catalog.xml")
        >>> utdquake.core.obspy.utdq_obspy_patch()
        >>> picks_df = cat.utdq_picks_to_df()
        >>> events_df = cat.utdq_events_to_df()
        >>> qc_cat = cat.apply_utdq_qc(debug=True)

    Notes
    -----
    - This patch is applied only if the methods are not already present on the
      :class:`Catalog` class, preventing accidental overwriting.
    - This is a runtime modification (monkey-patching) of a third-party class.
    """
    # Monkey-patch methods into ObsPy Catalog if they do not already exist
    if not hasattr(Catalog, "utdq_picks_to_df"):
        Catalog.utdq_picks_to_df = utdq_picks_to_df

    if not hasattr(Catalog, "utdq_events_to_df"):
        Catalog.utdq_events_to_df = utdq_events_to_df

    if not hasattr(Catalog, "apply_utdq_qc"):
        Catalog.apply_utdq_qc = apply_utdq_qc


class EventBank(ObsplusEventBank):
    """
    Extended EventBank with safe event deletion utilities.
    """



    def get_stations(self, query: Optional[str] = None) -> pd.DataFrame:
        """
        Return a summary of stations.

        Args:
            query (Optional[str]): SQL query string.

        Returns:
            pd.DataFrame: DataFrame with station information.
        """
        
        if query is None:
            query = """
                SELECT *
                FROM '/stations/index'
                WHERE rowid IN (
                    SELECT MIN(rowid)
                    FROM '/stations/index'
                    GROUP BY network, station
                )
            """

        conn = sqlite3.connect(self.index_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def to_parquet(self, path, chunk_size=5000, apply_utd_qc=True, 
                   events=True, picks=True, overwrite=True,
                   qc_debug=True):
        """
        Export events and picks to Parquet format with optional UTD QC.

        Parameters
        ----------
        path : Path
            Output directory.
        events : bool
            Export events.
        picks : bool
            Export picks.
        apply_utd_qc : bool
            Apply UTD QC before exporting.
        chunk_size : int
            Number of events per chunk.
        overwrite : bool
            Reset progress and rebuild.
        qc_debug : bool
            If True, print debug info during UTD QC.
        """
        to_parquet(bank=self, path=path, events=events, picks=picks,
                   apply_utd_qc=apply_utd_qc, chunk_size=chunk_size,
                   overwrite=overwrite,qc_debug=qc_debug)


    def delete_events(self, event_ids, test=True, verbose=True):
        """
        Remove one or multiple events from the EventBank.

        Parameters
        ----------
        event_ids : str or list of str
            Event resource ID(s) to remove.
        test : bool, default True
            If True, perform a dry run (no files deleted).
        verbose : bool, default True
            If True, print deletion summary.

        Returns
        -------
        list of str
            List of event IDs that were found in the bank.
        """

        # Allow single ID
        if isinstance(event_ids, str):
            event_ids = [event_ids]

        df = self.read_index()
        removed = []
        file_paths = []

        for ev_id in event_ids:
            row = df[df["event_id"] == ev_id]
            if not row.empty:
                removed.append(ev_id)
                file_paths.append(row.iloc[0]["path"])
            elif verbose:
                print(f"Event {ev_id} not found in bank.")

        if verbose:
            print("\n#### Delete Events Summary ####")
            print(f"Requested: {len(event_ids)}")
            print(f"Found:     {len(removed)}")

        if test:
            if verbose:
                print("TEST MODE: No files were deleted.")
                for path in file_paths:
                    print(f"  Would remove: {path}")
            return removed

        # Actual deletion
        for path in file_paths:
            os.remove(path)

        if file_paths:
            self.update_index()

        if verbose:
            print(f"Deleted {len(file_paths)} events.")
            print("Index updated.\n")

        return removed