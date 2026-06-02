from __future__ import annotations
import sys
import shutil
import glob
import os
import time
import sqlite3
import datetime
import concurrent.futures as cf
import pandas as pd
import obsplus
import logging
from obspy import read_events
from typing import Iterable, List, Optional, Union
from obspy.core.event import Catalog, Event
from . import utils as ut
from ..utils.utils import get_network_summary
from ..core.config import get_utdq_paths
from ..qc.config import PICK_TT_QC_DEFAULTS
from ..qc.travel_time import (
                            TravelTime,
                            TravelTimeModel)
from ..writers.schema import (sanitize_dataframe, 
                            PREF_EVENTS_ORDER,
                            PREF_EVENTS_TYPES,
                            PREF_PICKS_ORDER, 
                            PREF_PICKS_TYPES,
                            PREF_STATIONS_ORDER,
                            PREF_STATIONS_TYPES
                            )
from ..utils.utils import get_network_summary

logger = logging.getLogger("utdquake.bank")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s:%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent duplicate logs if root logging is configured later
    logger.propagate = False

class UTDQBank(obsplus.EventBank):
    """
    Extension of :class:`obsplus.EventBank` with batch ingestion utilities.

    This subclass adds functionality to efficiently load seismic event files
    from a directory using parallel processing and chunking.

    Notes
    -----
    - put_utdq_stations() is designed to process events in time chunks, appending station
    - put_utdq_picks() saves picks in chunks to a separate SQLite DB, tracking progress to avoid duplicates.

    Args:
        bank_path (str): Path to the event bank.
        das (bool): Whether to use the DAS dataset paths. Default is False.
        *args
            Positional arguments passed to :class:`obsplus.EventBank`.
        **kwargs
            Keyword arguments passed to :class:`obsplus.EventBank`.
    """
    def __init__(self, *args, das: bool = False, **kwargs) -> None:
        """
        Initialize EventBank.
        """
        super().__init__(*args, **kwargs)
        self.das = das
        self.contributor = os.path.basename(self.bank_path)
        self.db_paths = self.__prepare_paths()

    def __prepare_paths(self) -> None:
        """
        Create the directory structure required for UTDQ exports.

        The following export directories are created if they do not
        already exist:

        - events
        - stations
        - picks

        Additionally, an auxiliary hidden directory is created inside
        the stations export directory for station-related metadata.

        Returns
        -------
        dict[str, pathlib.Path]
            Mapping between UTDQ path keys and their corresponding
            database or directory paths.
        """
        paths = get_utdq_paths(self.contributor, das=self.das)

        key_export_path = ".utdquake/export/db"
        export_path = paths[key_export_path]

        folders_to_create = ["events","stations","picks"]
        utdq_db_paths = {}

        for folder in folders_to_create:
            key_path = "/".join([key_export_path, folder])
            path = export_path / folder
            db_path = path / f"{self.contributor}.db"

            utdq_db_paths[key_path] = db_path
            path.mkdir(parents=True, exist_ok=True)

            if folder == "stations":
                add_path = path / f".{self.contributor}"
                key_add_path = "/".join([key_path, ".stations"])
                utdq_db_paths[key_add_path] = add_path
                add_path.mkdir(parents=True, exist_ok=True)
        
        return utdq_db_paths
        

    @property
    def index_table_names(self) -> List[str]:
        """Return all table names in the event bank index."""
        return ut.get_table_names(self.index_path)

    @property
    def picks_table_names(self) -> List[str]:
        """Return all table names in the picks bank index."""
        if not os.path.exists(self.utdq_paths[".utdquake/export/db/picks"]):
            raise FileNotFoundError(
                f'Picks database not found at {self.utdq_paths[".utdquake/export/db/picks"]}. '
                "Please run 'save_picks()' to create it."
            )
        return ut.get_table_names(self.utdq_paths[".utdquake/export/db/picks"])

    def get_summary(self) -> dict:
        """Return a summary of the event bank contents."""
        stations = self.load_stations()
        events = self.load_events()
        return get_network_summary(stations=stations,events=events,
                                    das=self.das)
    
    @staticmethod
    def _read_events_parallel(
        files: Iterable[str],
        max_workers: int = 4,
    ) -> List[Event]:
        """
        Read multiple event files in parallel.

        Parameters
        ----------
        files : Iterable[str]
            List or iterable of file paths.
        max_workers : int, optional
            Number of threads to use. Default is 4.

        Returns
        -------
        list of obspy.core.event.Event
            Flattened list of events read from all files.

        Notes
        -----
        This function avoids shared mutable state across threads by returning
        results from each worker and combining them afterward.
        """

        def _process_file(file_path: str) -> List[Event]:
            """
            Read a single file and return its events.

            Parameters
            ----------
            file_path : str
                Path to the event file.

            Returns
            -------
            list of Event
                Events contained in the file.
            """
            try:
                catalog = read_events(file_path)
                return list(catalog)
            except Exception as exc:  # noqa: BLE001
                # Log and skip problematic files
                # print(f"Error reading {file_path}: {exc}")
                logger.error(f"Error reading {file_path}: {exc}")
                return []

        # Execute file reading in parallel
        with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(_process_file, files)

        # Flatten list of lists into a single list of events
        events: List[Event] = [
            event for sublist in results for event in sublist
        ]

        return events

    def __stations_sanity_check(self) -> bool:
        """ Check if station details path exists."""
        if not os.path.isdir(self.utdq_paths[".utdquake/export/db/stations/.stations"]):
            logger.warning("Station details path does not exist.")
            return False
        return True

    @staticmethod
    def _chunk_list(lst: List[str], n: int):
        """Yield successive n-sized chunks from a list."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    @staticmethod
    def _initialize_progress_table(conn: sqlite3.Connection, table_name: str) -> None:
        """Create progress table if it does not exist."""
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS '{table_name}' (
                event_id TEXT PRIMARY KEY
            )
        """)
        conn.commit()

    @staticmethod
    def _get_processed_event_ids(conn: sqlite3.Connection, table_name: str) -> set:
        """Return a set of already processed event IDs."""
        df = pd.read_sql_query(f"SELECT event_id FROM '{table_name}'", conn)
        return set(df["event_id"].values)

    @staticmethod
    def _save_chunk_to_db(df: pd.DataFrame, table_name: str, conn: sqlite3.Connection, table_exists: bool) -> None:
        """Save a chunk of picks to the database."""
        if not table_exists:
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        else:
            df.to_sql(
                        table_name,
                        conn,
                        if_exists="append",
                        index=False,
                        method="multi",
                        chunksize=80,
                    )
        conn.commit()

    @staticmethod
    def _update_progress_table(event_ids: List[str], table_name: str, conn: sqlite3.Connection) -> None:
        """Update the progress table with processed event IDs."""
        progress_df = pd.DataFrame({"event_id": event_ids})
        progress_df.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
        conn.commit()

    def put_utdq_events(self):
        """Lazy implementation"""
        shutil.copy(self._index_path, self.utdq_paths[".utdquake/export/db/events"])


    def put_utdq_events_from_folder(
        self,
        folder_path: str,
        file_extension: str = "*.xml",
        chunk_size: int = 100,
        max_workers: int = 4,
        ) -> None:
        """
        Load and store events from files in a folder.

        This method scans a directory for event files, reads them in parallel,
        groups them into chunks, and inserts them into the EventBank.

        Parameters
        ----------
        folder_path : str
            Path to the directory containing event files.
        file_extension : str, optional
            Glob pattern for file matching (e.g., "*.xml", "*.quakeml").
            Default is "*.xml".
        chunk_size : int, optional
            Number of files to process per batch. Default is 100.
        max_workers : int, optional
            Number of threads for parallel file reading. Default is 4.

        Raises
        ------
        FileNotFoundError
            If the folder does not exist.

        Examples
        --------
        >>> bank = EventBank("my_bank")
        >>> bank.put_events_from_folder("events/", "*.xml", chunk_size=50)
        """
        if not os.path.isdir(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Build full glob pattern (e.g., /path/to/folder/*.xml)
        pattern = os.path.join(folder_path, file_extension)

        # Retrieve all matching files
        files: List[str] = glob.glob(pattern, recursive=True)

        # Split files into chunks to control memory usage
        chunked_files: List[List[str]] = [
            files[i : i + chunk_size]
            for i in range(0, len(files), chunk_size)
        ]

        # print(
        #     f"Total files: {len(files)}, "
        #     f"Chunk size: {chunk_size}, "
        #     f"Total chunks: {len(chunked_files)}"
        # )

        logger.info(f"Total files found: {len(files)} | "
                    f"Chunk size: {chunk_size} | "
                    f"Total chunks to process: {len(chunked_files)}")

        # Process each chunk sequentially (parallelism inside each chunk)
        for idx, chunk in enumerate(chunked_files, start=1):
            # print(
            #     f"Processing chunk {idx}/{len(chunked_files)} "
            #     f"with {len(chunk)} files"
            # )

            logger.info(f"Processing chunk {idx}/{len(chunked_files)} | "
                        f"Files in chunk: {len(chunk)}")

            # Read files in parallel and collect results safely
            events: List[Event] = self._read_events_parallel(
                chunk, max_workers=max_workers
            )

            # Create ObsPy Catalog from collected events
            catalog = Catalog(events=events)

            # Store events in the EventBank
            self.put_events(catalog)


    def put_utdq_stations(self, stations, starttime=None, endtime=None,
                        chunk_seconds=86400,
                        das=False,
                        calculate_d_az=True) -> None:
        """
        Save station metadata to events in the event bank over a given time range.

        The catalog is processed in time chunks. For each chunk:
        - Events are loaded from the catalog generator
        - Station information is appended to each event
        - Valid events are stored in the event bank
        - A stations summary table is updated in the event bank index

        Parameters
        ----------
        stations : pandas.DataFrame
            DataFrame containing station metadata with columns:
            ['network', 'station', 'latitude', 'longitude'].
        starttime : obspy.UTCDateTime
            Start time of the catalog processing window.
        endtime : obspy.UTCDateTime
            End time of the catalog processing window.
        chunk_seconds : int
            Length of each processing chunk in seconds.
        calculate_d_az : bool, optional
            Whether to calculate distance and azimuth between
            events and stations (default is True).

        """
        
        ebank_index_path = os.path.join(self.bank_path, ".index.db")

        if starttime is None:
            starttime = self.read_index()["time"].min()
        if endtime is None:
            endtime = self.read_index()["time"].max()

        iteration = 0
        for catalog_dict  in ut.catalog_generator(self,starttime=starttime,
                                endtime= endtime,
                                chunk_seconds=chunk_seconds,
                                orderby=False):

            catalog = catalog_dict["catalog"]
            original_len_catalog = len(catalog)
            chunk_starttime = catalog_dict["starttime"].strftime("%Y-%m-%d %H:%M:%S.%f")
            chunk_endtime = catalog_dict["endtime"].strftime("%Y-%m-%d %H:%M:%S.%f")
            chunk_creation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            logger.info(f"Chunk id: {iteration:<3} initiated | "
                        f"Time range: {chunk_starttime} - {chunk_endtime} | "
                        f"Chunk creation time: {chunk_creation_time}")

            catalog = ut.append_stations_to_catalog(catalog=catalog, 
                                                    df_stations=stations,
                                                    calculate_d_az=calculate_d_az,
                                                    ebank_index_path=ebank_index_path,
                                                    das=das
                                                                )

            new_len_catalog = len(catalog)

            ### putting events
            try:
                self.put_events(catalog)
                logger.info(f"Saved {new_len_catalog} events of {original_len_catalog} possible in chunk id {iteration:<3} "
                            f"from {chunk_starttime} to {chunk_endtime} in {self.bank_path}")
            except Exception as e:
                error_patience_counter += 1
                logger.error(f"Failed to save events: {e}. "
                            )
                logger.warning(
                                    f"Chunk id {iteration:<3} has no acceptable events. "
                                    f"Start time: {chunk_starttime}, End time: {chunk_endtime}. "
                                    f"Continuing to next chunk.")
                continue
            

            logger.info(f"Creating stations summary based on the events in the event bank at {self.bank_path}")
            # stations_folder = os.path.join( self.bank_path,".stations")

            stations_folder = self.utdq_paths[".utdquake/export/db/stations/.stations"]
            stations_db = self.utdq_paths[".utdquake/export/db/stations"]
            logger.info(f"Loading station details from {stations_folder} to create summary.")
            summary = ut.get_stations_summary(stations_folder=stations_folder)
            if summary is not None:
                logger.info(f"Updating stations summary in the event bank at {self.bank_path}")
                logger.info(f"Preparing stations database at {stations_db} to save {len(summary)} stations.")
                with sqlite3.connect(stations_db) as ev_con:
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

    def put_utdq_picks(
        self,
        chunk_size: int = 100,
        event_id: Optional[List[str]] = None,
        replace: bool = False,
        apply_utdq_qc: bool = True,
    ) -> None:
        """
        Save picks and events to SQLite DBs in chunks, avoiding duplicates.

        This implementation ensures:
        - Atomic writes (picks + events + progress)
        - Safe restart (idempotent ingestion)
        - No progress corruption

        Args:
            chunk_size (int): Number of events to process per chunk.
            event_id (Optional[List[str]]): Specific event IDs to process.
            replace (bool): If True, deletes existing DBs and rebuilds from scratch.
            apply_utdq_qc (bool): Whether to apply QC to picks before saving.
        """

        picks_table_name = "/picks/index"
        events_table_name = "/events/index"
        progress_table = "/progress"

        tic = time.time()

        # --- Reset DBs if requested ---
        if replace:
            if os.path.exists(self.utdq_paths[".utdquake/export/db/picks"]):
                logger.warning("Deleting picks DB: %s", self.utdq_paths[".utdquake/export/db/picks"])
                os.remove(self.utdq_paths[".utdquake/export/db/picks"])
            if os.path.exists(self.utdq_paths[".utdquake/export/db/events"]):
                logger.warning("Deleting events DB: %s", self.utdq_paths[".utdquake/export/db/events"])
                os.remove(self.utdq_paths[".utdquake/export/db/events"])

        # --- Determine event IDs ---
        if event_id is None:
            index = self.read_index().sort_values("event_id")
            all_ids = index.event_id.values
        else:
            if isinstance(event_id, str):
                event_id = [event_id]
            all_ids = event_id

        # --- Open DB connections ---
        picks_conn = sqlite3.connect(self.utdq_paths[".utdquake/export/db/picks"])
        events_conn = sqlite3.connect(self.utdq_paths[".utdquake/export/db/events"])

        try:
            # --- SQLite performance tuning ---
            picks_conn.execute("PRAGMA journal_mode=WAL;")
            events_conn.execute("PRAGMA journal_mode=WAL;")

            # --- Initialize progress table (only once, in picks DB) ---
            self._initialize_progress_table(picks_conn, progress_table)

            # --- Determine what to process ---
            processed_event_ids = self._get_processed_event_ids(picks_conn, progress_table)
            to_process_ids = [eid for eid in all_ids if eid not in processed_event_ids]

            if not to_process_ids:
                logger.info("All events are already saved.")
                return

            logger.info(
                "Total events: %d | Already processed: %d | To process: %d",
                len(all_ids),
                len(processed_event_ids),
                len(to_process_ids),
            )

            total_chunks = (len(to_process_ids) + chunk_size - 1) // chunk_size

            # --- Check if tables already exist ---
            picks_table_exists = picks_table_name in ut.get_table_names(self.utdq_paths[".utdquake/export/db/picks"])
            events_table_exists = events_table_name in ut.get_table_names(self.utdq_paths[".utdquake/export/db/events"])

            # --- Process chunks ---
            for i, ev_chunk_ids in enumerate(self._chunk_list(to_process_ids, chunk_size), start=1):

                try:
                    catalog = self.get_events(event_id=ev_chunk_ids)

                    if apply_utdq_qc:
                        logger.info(
                            "Applying QC to %d events (chunk %d/%d)",
                            len(ev_chunk_ids),
                            i,
                            total_chunks,
                        )
                        catalog.apply_utdq_qc()

                    events_df = catalog.utdq_events_to_df()
                    picks_df = catalog.utdq_picks_to_df()

                    if picks_df.empty:
                        logger.warning("Chunk %d is empty. Skipping.", i)
                        continue

                    # --- Begin atomic transaction ---
                    picks_conn.execute("BEGIN")
                    events_conn.execute("BEGIN")

                    # --- Save data ---
                    self._save_chunk_to_db(
                        picks_df, picks_table_name, picks_conn, picks_table_exists
                    )
                    self._save_chunk_to_db(
                        events_df, events_table_name, events_conn, events_table_exists
                    )

                    # --- Update progress ONLY after successful writes ---
                    self._update_progress_table(ev_chunk_ids, progress_table, picks_conn)

                    # --- Commit both DBs ---
                    picks_conn.commit()
                    events_conn.commit()

                    picks_table_exists = True
                    events_table_exists = True

                    logger.info(
                        "Chunk %d/%d saved successfully (%d events)",
                        i,
                        total_chunks,
                        len(ev_chunk_ids),
                    )

                except Exception as e:
                    # --- Rollback both DBs on failure ---
                    picks_conn.rollback()
                    events_conn.rollback()

                    logger.error(
                        "Chunk %d/%d failed: %s",
                        i,
                        total_chunks,
                        str(e),
                    )
                    continue

            toc = time.time()
            logger.info("Saving picks completed in %.2f seconds", toc - tic)

        finally:
            # --- Always close connections ---
            picks_conn.close()
            events_conn.close()


    def load_stations(self, query: Optional[str] = None) -> pd.DataFrame:
        """
        Return a summary of stations.

        Args:
            query (Optional[str]): SQL query string.

        Returns:
            pd.DataFrame: DataFrame with station information.
        """
        if query is None:
            if self.das:
                query = """
                    SELECT *
                    FROM '/stations/index'
                    WHERE rowid IN (
                        SELECT MIN(rowid)
                        FROM '/stations/index'
                        GROUP BY network, station, channel
                    )
                """
            else:
                query = """
                    SELECT *
                    FROM '/stations/index'
                    WHERE rowid IN (
                        SELECT MIN(rowid)
                        FROM '/stations/index'
                        GROUP BY network, station
                    )
                """

        df = ut._read_table(self.index_path, query)

        df = sanitize_dataframe(df,
                                order_cols=PREF_STATIONS_ORDER,
                                string_cols=PREF_STATIONS_TYPES["string_cols"],
                                float_cols=PREF_STATIONS_TYPES["float_cols"],
                                int_cols=PREF_STATIONS_TYPES["int_cols"],
                                datetime_cols=PREF_STATIONS_TYPES["datetime_cols"],
                                bool_cols=PREF_STATIONS_TYPES["bool_cols"],
                                )


        return df

    def load_events(
                self,
                query: Optional[str] = None,
                 
                ) -> pd.DataFrame:
        """
        Load picks either from the picks database or from the manifest files.

        Args:
            query (Optional[str]): SQL query string (used only for sql fmt).

        Returns:
            pd.DataFrame: DataFrame of picks.
        """
        
        if not os.path.exists(self.utdq_paths[".utdquake/export/db/picks"]):
            raise FileNotFoundError(
                f'Events database not found at {self.utdq_paths[".utdquake/export/db/picks"]}. '
                "Please run 'put_events()' to create it."
            )

        if query is None:
            query = """
                SELECT *
                FROM '/events/index'
                WHERE event_id IN (
                    SELECT event_id
                    FROM '/events/index'
                    GROUP BY event_id
                    HAVING COUNT(*) = 1
                )
            """
        df = ut._read_table(self.utdq_paths[".utdquake/export/db/events"], query)

        df = sanitize_dataframe(df, 
                                order_cols=PREF_EVENTS_ORDER, 
                                **PREF_EVENTS_TYPES)

        return df

    def load_picks(
                self,
                query: Optional[str] = None,
                 
                ) -> pd.DataFrame:
        """
        Load picks either from the picks database or from the manifest files.

        Args:
            query (Optional[str]): SQL query string (used only for sql fmt).

        Returns:
            pd.DataFrame: DataFrame of picks.
        """
        
        if not os.path.exists(self.utdq_paths[".utdquake/export/db/picks"]):
            raise FileNotFoundError(
                f'Picks database not found at {self.utdq_paths[".utdquake/export/db/picks"]}. '
                "Please run 'put_picks()' to create it."
            )

        if query is None:
            query = """
                SELECT *
                FROM '/picks/index'
                WHERE pick_id IN (
                    SELECT pick_id
                    FROM '/picks/index'
                    GROUP BY pick_id
                    HAVING COUNT(*) = 1
                )
            """
        df = ut._read_table(self.utdq_paths[".utdquake/export/db/picks"], query)

        df = sanitize_dataframe(df, 
                                order_cols=PREF_PICKS_ORDER, 
                                **PREF_PICKS_TYPES)

        return df

