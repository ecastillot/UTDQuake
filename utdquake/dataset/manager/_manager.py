import os
import pandas as pd
import numpy as np
import sqlite3
from typing import  Optional
from obsplus import EventBank as ObsplusEventBank

from ..writers.parquet import to_parquet

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