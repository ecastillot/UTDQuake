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
        self.stations_from_eqs_path = os.path.join(self.bank_path, ".stations")
        self.picks_path = os.path.join(self.bank_path, ".picks.db")
        self.contributor = os.path.basename(self.bank_path)


    @property
    def index_table_names(self) -> List[str]:
        """Return all table names in the event bank index."""
        return fut.get_table_names(self.index_path)

    @property
    def picks_table_names(self) -> List[str]:
        """Return all table names in the picks bank index."""
        if not os.path.exists(self.picks_path):
            raise FileNotFoundError(
                f"Picks database not found at {self.picks_path}. "
                "Please run 'save_picks()' to create it."
            )
        return fut.get_table_names(self.picks_path)

    @property
    def stats(self):
        """Return summary statistics of the event bank."""
        analysis, events, stations = self._get_analysis()
        return analysis

    def __str__(self,extended=False) -> str:
        """Return string representation of the EventBank."""
        base_info = super().__str__()
        if extended:
            stats = self.stats
            stats_info = "\n".join(f"\t{key}: {value}" for key, value in stats.items())
            return f"{base_info}\n{stats_info}"
        
        msg = "Use .__str__(True) to see more details."
        return base_info+f"... {msg}"

    # station methods

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

    def get_stations_from_eqs(
        self,
        stations: Optional[List[str]] = None,
        networks: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Retrieve details for selected stations. 
        The station locations were calculated from earthquake data.

        Args:
            stations (Optional[List[str]]): List of station names to filter.
            networks (Optional[List[str]]): List of network codes to filter.

        Returns:
            pd.DataFrame: Combined station details.
        """
        all_station_details = []

        for filename in os.listdir(self.stations_from_eqs_path):
            # Extract network and station name
            name = os.path.splitext(filename)[0].split(".")[1]
            network, station = name.split("_")

            if networks and network not in networks:
                continue
            if stations and station not in stations:
                continue

            station_path = os.path.join(self.stations_from_eqs_path, filename)
            query = "SELECT * FROM '/stations/index'"
            details = fut._read_table(station_path, query)
            all_station_details.append(details)

        if not all_station_details:
            logger.warning("No station details found for the given filters.")
            return pd.DataFrame()

        return pd.concat(all_station_details, ignore_index=True)

    def append_stations(self, stations, starttime, endtime,
                        chunk_seconds,
                        calculate_d_az=True) -> None:
        """
        Append station metadata to events in the event bank over a given time range.

        The catalog is processed in time chunks. For each chunk:
        - Events are loaded from the catalog generator
        - Station information is appended to each event
        - Valid events are stored in the event bank
        - A stations summary table is updated in the event bank index

        Parameters
        ----------
        stations : pandas.DataFrame
            DataFrame containing station metadata.
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

            catalog = fut.append_stations_to_catalog(catalog=catalog, 
                                                    df_stations=stations,
                                                    calculate_d_az=calculate_d_az,
                                                    ebank_index_path=ebank_index_path,
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

    # picks methods

    def get_picks(self, event_ids: List[str]) -> pd.DataFrame:
        """
        Retrieve and merge picks and arrivals for a list of event IDs.

        This method loads the events from the event bank, converts both picks and
        arrivals to pandas DataFrames, and merges them into a single table using
        the project-specific merge logic.

        Parameters
        ----------
        event_ids : list of str
            List of event identifiers to retrieve.

        Returns
        -------
        pandas.DataFrame
            DataFrame containing merged pick and arrival information.
        """
        catalog = self.get_events(event_id=event_ids)
        picks = catalog.picks_to_df()
        arrivals = catalog.arrivals_to_df()
        return fut.merge_arrivals_and_picks(arrivals, picks)

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
            df = self.get_picks(chunk_ids)
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

    def load_picks(self, query: Optional[str] = None,
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

    #plotting functions
    
    def plot_overview(self,savepath: str=None) -> None:
        """
        Plot a network map with events, stations, histograms, globe, and region.

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        
        analysis,events,stations = self._get_analysis()

        stations = stations.rename(columns={"calculated_longitude": "longitude",
                                                "calculated_latitude": "latitude",
                                                "calculated_elevation": "elevation"})

        plot_overview(events=events, stations=stations,
                        analysis=analysis,
                        output_file=savepath)
        
    def plot_stats(self,savepath: str=None) -> None:
        """
        Create a 5-panel seismic overview figure:
            - Depth histogram
            - Magnitude histogram
            - Epicentral distance distribution (requires picks)
            - Azimuthal gap (from events)
            - Azimuth distribution (requires picks)
        
        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        events = self.read_index()
        try:
            picks = self.load_picks()
        except FileNotFoundError:
            logger.error("Picks database not found. Please run 'save_picks()' first.")

        plot_stats(events, picks, savepath)

    def plot_uncertainty_boxplots(self, savepath: str=None) -> None:
        """
        Create a figure with two axes:
        1. Boxplots for Horizontal and Vertical uncertainty (km)
        2. Boxplot for Standard error

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        events = self.read_index()
        plot_uncertainty_boxplots(events, save_path=savepath)

    def plot_pick_stats(self, savepath: str=None) -> None:
        """
        Plot summary statistics for seismic picks (P, S, and S-P) as jointplots.

        This function computes:
        - First/last P travel times per event
        - First/last S travel times per event
        - First/last S-P times for stations that have both P and S picks
        - Corresponding epicentral distances (converted to km)

        It creates individual seaborn jointplots (scatter + marginal histograms),
        saves them temporarily as PNGs, and then combines them into a single
        multi-panel matplotlib figure.

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        picks = self.load_picks()
        plot_pick_stats(picks, save_path=savepath)

    def plot_station_location_uncertainty(self, savepath: str=None) -> None:
        """
        Compare confirmed vs calculated latitude and longitude in a DataFrame.

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        stations = self.get_stations()
        plot_station_location_uncertainty(stations, savepath)

    def plot_pick_histograms(self, savepath: str=None) -> None:
        """
        Plots three histograms:
        1. Number of P picks per origin
        2. Number of S picks per origin
        3. Vp/Vs ratio histogram using Wadati method

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        picks = self.load_picks()
        plot_pick_histograms(picks, save_path=savepath)

    ## others

    def _get_analysis(self):
        """
        Compute summary statistics for the event bank.

        This method gathers information about:
        - Total number of events with valid locations
        - Station availability and confirmation status
        - Number of P and S phase arrivals
        - Dataset contributor metadata

        Returns
        -------
        tuple
            A tuple containing:
            - analysis : dict
                Dictionary with summary statistics.
            - events : pandas.DataFrame
                DataFrame of events with valid latitude and longitude.
            - stations : pandas.DataFrame
                DataFrame of unique stations used in the analysis.
        """
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
                        "P arrivals": int(n_p_picks),
                        "S arrivals": int(n_s_picks),
                        "contributor": self.contributor
                }
        return analysis,events,stations

    def __stations_sanity_check(self) -> bool:
        """ Check if station details path exists."""
        if not os.path.isdir(self.stations_from_eqs_path):
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
            df.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
        conn.commit()

    @staticmethod
    def _update_progress_table(event_ids: List[str], table_name: str, conn: sqlite3.Connection) -> None:
        """Update the progress table with processed event IDs."""
        progress_df = pd.DataFrame({"event_id": event_ids})
        progress_df.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
        conn.commit()
