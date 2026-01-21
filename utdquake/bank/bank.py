import os
import time
import sqlite3
import logging
from typing import List, Optional, Union
import pandas as pd
import obsplus
import matplotlib.pyplot as plt
from . import utils as fut
from . import setup_logger, add_file_handler
import datetime
from utdquake.utils.plot import (plot_overview,plot_stats,
                                 plot_station_location_uncertainty,
                                 plot_pick_histograms,
                                 plot_uncertainty_boxplots,
                                 plot_pick_stats)

logger = logging.getLogger(__name__)
setup_logger(logging_level=logging.INFO)


class EventBank(obsplus.EventBank):
    """
    EventBank extension for handling picks and station data.
    """

    def __init__(self, bank_path: str, *args, **kwargs) -> None:
        """
        Initialize EventBank.

        Args:
            bank_path (str): Path to the event bank.
        """
        super().__init__(bank_path, *args, **kwargs)
        self.station_details_path = os.path.join(self.bank_path, ".stations")
        self.picks_path = os.path.join(self.bank_path, ".picks.db")
        self.contributor = os.path.basename(self.bank_path)

    @property
    def index_table_names(self) -> List[str]:
        """Return all table names in the event bank index."""
        return fut.get_table_names(self.index_path)

    def stations_sanity_check(self) -> bool:
        """ Check if station details path exists."""
        if not os.path.isfile(self.station_details_path):
            logger.warning("Station details path does not exist.")
            return False
        return True



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
        return fut._read_table(self.index_path, query)

    

    def get_picks(self, query: Optional[str] = None,
                  time_columns = ['time','origin_time']) -> pd.DataFrame:
        """
        Return unique picks from the picks database.

        Args:
            query (Optional[str]): SQL query string.

        Returns:
            pd.DataFrame: DataFrame of picks.
        """
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
        if not os.path.exists(self.picks_path):
            raise FileNotFoundError(
                f"Picks database not found at {self.picks_path}. "
                "Please run 'save_picks()' to create it."
            )
        df = fut._read_table(self.picks_path, query)
        #convert time columns to datetime
        
        for col in time_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        return df

    def get_stations_details(
        self,
        stations: Optional[List[str]] = None,
        networks: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Retrieve details for selected stations.

        Args:
            stations (Optional[List[str]]): List of station names to filter.
            networks (Optional[List[str]]): List of network codes to filter.

        Returns:
            pd.DataFrame: Combined station details.
        """
        all_station_details = []

        for filename in os.listdir(self.station_details_path):
            # Extract network and station name
            name = os.path.splitext(filename)[0].split(".")[1]
            network, station = name.split("_")

            if networks and network not in networks:
                continue
            if stations and station not in stations:
                continue

            station_path = os.path.join(self.station_details_path, filename)
            query = "SELECT * FROM '/stations/index'"
            details = fut._read_table(station_path, query)
            all_station_details.append(details)

        if not all_station_details:
            logger.warning("No station details found for the given filters.")
            return pd.DataFrame()

        return pd.concat(all_station_details, ignore_index=True)

    def _get_picks_from_chunk(self, event_ids: List[str]) -> pd.DataFrame:
        """Process a chunk of event IDs to extract picks."""
        catalog = self.get_events(event_id=event_ids)
        picks = catalog.picks_to_df()
        arrivals = catalog.arrivals_to_df()
        return fut.merge_arrivals_and_picks(arrivals, picks)

    def append_stations(self, stations, starttime, endtime,
                        chunk_seconds,
                        calculate_d_az=True) -> None:
        
        ebank_index_path = os.path.join(self.bank_path, ".index.db")

        iteration = 0
        for catalog_dict  in fut.catalog_generator(self,starttime=starttime,
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

            # print(catalog)
            catalog = fut.append_stations_to_catalog(catalog=catalog, 
                                                    df_stations=stations,
                                                    calculate_d_az=calculate_d_az,
                                                    ebank_index_path=ebank_index_path,
                                                                )
            # print(catalog)

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
            

            logger.info(f"Creating stations summary based on the events in the event bank at {self.bank_path}/.stations")
            stations_folder = os.path.join( self.bank_path,".stations")
            summary = fut.get_stations_summary(stations_folder=stations_folder)
            if summary is not None:
                logger.info(f"Updating stations summary in the event bank at {self.bank_path}")
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


    def save_picks(self, chunk_size: int = 100, event_id: Optional[List[str]] = None) -> None:
        """
        Save picks to SQLite DB in chunks, avoiding duplicates.

        Args:
            chunk_size (int): Number of events to process per chunk.
            event_id (Optional[List[str]]): Specific event IDs to process.
        """
        picks_table_name = "/picks/index"
        progress_table_name = "/picks/progress"
        tic = time.time()

        # Determine event IDs
        if event_id is None:
            index = self.read_index().sort_values("event_id")
            all_ids = index.event_id.values
        else:
            all_ids = event_id

        conn = sqlite3.connect(self.picks_path)
        self._initialize_progress_table(conn, progress_table_name)
        processed_event_ids = self._get_processed_event_ids(conn, progress_table_name)
        to_process_ids = [eid for eid in all_ids if eid not in processed_event_ids]

        if not to_process_ids:
            logger.info("All events are already saved.")
            conn.close()
            return

        logger.info(
            "Total events: %d, Already processed: %d, To process: %d",
            len(all_ids),
            len(processed_event_ids),
            len(to_process_ids),
        )

        total_chunks = (len(to_process_ids) + chunk_size - 1) // chunk_size
        table_exists = picks_table_name in fut.get_table_names(self.picks_path)

        for i, chunk_ids in enumerate(self._chunk_list(to_process_ids, chunk_size), start=1):
            df = self._get_picks_from_chunk(chunk_ids)
            if df.empty:
                logger.warning("Chunk %d is empty. Skipping.", i)
                continue

            self._save_chunk_to_db(df, picks_table_name, conn, table_exists)
            self._update_progress_table(chunk_ids, progress_table_name, conn)
            table_exists = True

            logger.info("Chunk %d/%d saved: %d events", i, total_chunks, len(chunk_ids))

        conn.close()
        toc = time.time()
        logger.info("Saving picks completed in %.2f seconds", toc - tic)

    def plot_overview(self,savepath: str=None) -> None:
        
        analysis,events,stations = self._get_analysis()

        stations = stations.rename(columns={"calculated_longitude": "longitude",
                                                "calculated_latitude": "latitude",
                                                "calculated_elevation": "elevation"})

        plot_overview(events=events, stations=stations,
                        analysis=analysis,
                        output_file=savepath)
        

    def plot_stats(self,savepath: str=None) -> None:
        events = self.read_index()
        try:
            picks = self.get_picks()
        except FileNotFoundError:
            logger.error("Picks database not found. Please run 'save_picks()' first.")

        plot_stats(events, picks, savepath)

    def plot_uncertainty_boxplots(self, savepath: str=None) -> None:
        events = self.read_index()
        plot_uncertainty_boxplots(events, save_path=savepath)

    def plot_pick_stats(self, savepath: str=None) -> None:
        picks = self.get_picks()
        plot_pick_stats(picks, save_path=savepath)

    def plot_station_location_uncertainty(self, savepath: str=None) -> None:
        stations = self.get_stations()
        plot_station_location_uncertainty(stations, savepath)

    def plot_pick_histograms(self, savepath: str=None) -> None:
        picks = self.get_picks()
        print(picks.info())
        plot_pick_histograms(picks, save_path=savepath)

    def _get_analysis(self):
        stations = self.get_stations()
        stations.drop_duplicates(subset=["network","station"], inplace=True)

        n_total_stations = len(stations)
        confirmed_stations = stations[stations["confirmed"]==True]
        calculated_stations = stations[stations["calculated"]==True]
        n_confirmed_stations = len(confirmed_stations)
        n_calculated_stations = len(calculated_stations)

        events = self.read_index()
        events = events.dropna(subset=["latitude","longitude"])
        n_p_picks = events['p_phase_count'].sum()
        n_s_picks = events['s_phase_count'].sum()

        analysis = {
                        "Events": len(events),
                        "Total Stations": n_total_stations,
                        "Calculated Stations": n_calculated_stations,
                        "Confirmed Stations": n_confirmed_stations,
                        "P arrivals": n_p_picks,
                        "S arrivals": n_s_picks,
                        "contributor": self.contributor
                }
        return analysis,events,stations


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
            df.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
        conn.commit()

    @staticmethod
    def _update_progress_table(event_ids: List[str], table_name: str, conn: sqlite3.Connection) -> None:
        """Update the progress table with processed event IDs."""
        progress_df = pd.DataFrame({"event_id": event_ids})
        progress_df.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
        conn.commit()
