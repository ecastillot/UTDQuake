# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-01-23 22:36:58
#  * @modify date 2025-01-23 22:36:58
#  * @desc [description]
#  */
from .data import DataFrameHelper
from ..database.database import load_from_sqlite,load_chunks_from_sqlite
from pandas.api.types import is_datetime64_any_dtype
import pandas as pd
import numpy as np
from typing import Optional
import matplotlib.pyplot as plt
from scipy.stats import linregress
import random

def read_picks(path, ev_ids=None, custom_params=None, drop_duplicates=True):
    """
    Load earthquake picks from an SQLite database and return a Picks object.

    Args:
        path (str): The path to the SQLite database file containing pick data.
        ev_ids (list of str, optional): List of event IDs (table names) to load picks from.
            If None, picks from all available tables are loaded. Defaults to None.
        custom_params (dict, optional): Custom filtering parameters for querying the database using mysql format. 
            Expected format: {column_name: {'value': value, 'condition': condition}}. 
            For example: To limit the search to 0.5 degrees of distance and stations started with OKAS.
                custom_params={"distance":{"condition":"<","value":0.5},
                                "station":{"condition":"LIKE","value":"OKAS%"}
                                  }.
            Defaults to None.
        drop_duplicates (bool, optional): Whether to drop duplicate rows from the data.
            Defaults to True.

    Returns:
        Picks: A Dataframe containing the loaded pick data and associated author information.

    Notes:
        - The data is sorted by the "time" column by default.
        - If `ev_ids` is None, all tables in the database are considered.
        - The `Picks` class must be defined elsewhere in your code to handle the loaded data.
    """
    # Load pick data from the SQLite database using the helper function
    picks = load_from_sqlite(
        db_path=path,           # Path to the SQLite database
        tables=ev_ids,          # Event IDs (table names) to load picks from
        custom_params=custom_params,  # Optional custom filtering parameters
        parse_dates=["time"],   # Parse the "time" column as datetime
        drop_duplicates=drop_duplicates,
        sortby="time"           # Sort the data by the "time" column
    )
    return picks
  
def read_picks_in_chunks(path, chunksize=100, custom_params=None, drop_duplicates=True):
    """
    Load earthquake picks from an SQLite database in chunks and yield a Picks object for each chunk.

    Args:
        path (str): The path to the SQLite database file containing pick data.
        chunksize (int, optional): The number of rows per chunk to load from the database. Defaults to 100,
            meaning the entire dataset will be loaded in one go. If specified, data will be loaded in chunks of the specified size.
        custom_params (dict, optional): Custom filtering parameters for querying the database using SQL format. 
            Expected format: {column_name: {'value': value, 'condition': condition}}. 
            Example: To limit the search to picks with a distance less than 0.5 degrees and stations starting with "OKAS":
                custom_params={"distance":{"condition":"<","value":0.5},
                               "station":{"condition":"LIKE","value":"OKAS%"}}.
            Defaults to None, meaning no additional filtering is applied.
        drop_duplicates (bool, optional): Whether to drop duplicate rows from the data.
            Defaults to True, meaning duplicates will be removed if present.

    Yields:
        Picks: A `Picks` object containing a chunk of the loaded pick data and associated author information.
            The function yields these `Picks` objects one by one, allowing for efficient processing of large datasets.

    Notes:
        - The data is sorted by the "time" column by default before being yielded.
        - The `Picks` class must be defined elsewhere in your code to handle and store the loaded data.
        - This function does not return a single result; it yields each chunk of data, allowing the caller to process them iteratively.
    """

    # Load pick data in chunks from the SQLite database using the helper function
    picks_in_chunks = load_chunks_from_sqlite(
        db_path=path,  # Path to the SQLite database containing pick data
        custom_params=custom_params,  # Optional custom filtering parameters to apply when querying the database
        drop_duplicates=drop_duplicates,  # Whether to remove duplicate rows from the data
        chunksize=chunksize,  # The number of rows per chunk to load from the database
        sortby="time"  # Sort the data by the "time" column in ascending order before yielding
    )

    # Iterate over each chunk of picks loaded from the database
    for picks in picks_in_chunks:
        # Yield a Picks object with the current chunk of picks and associated author information
        # This allows the caller to process each chunk one by one, without loading all the data into memory at once
        yield picks

class Picks(DataFrameHelper):
    """
    A class to manage and process earthquake picks data.

    Attributes:
    -----------
    data : pd.DataFrame
        The main DataFrame containing pick information. 
        Required columns: 'ev_id', 'network', 'station', 'time', 'phase_hint'.
    author : str, optional
        The author or source of the picks data.
    """
    
    def __init__(self, data, author) -> None:
        """
        Initialize the Picks class with mandatory columns.

        Parameters:
        -----------
        data : pd.DataFrame
            A DataFrame containing picks data. 
            Required columns: 'ev_id', 'network', 'station', 'time', 'phase_hint'.
        author : str, optional
            The author or source of the picks data.
        """
        mandatory_columns = ['ev_id', 'network', 'station', 'time', 'phase_hint']
        pick_id =lambda x: f"{x['phase_hint']}_{x['network']}_{x['station']}_{x['time'].strftime('%Y%m%dT%H%M%S.%f')}" if is_datetime64_any_dtype(x['time']) else f"{x['phase_hint']}_{x['network']}_{x['station']}_{x['time']}"
        data["pick_id"] = data.apply(pick_id, axis=1)
        super().__init__(data=data, required_columns=mandatory_columns,
                        date_columns=["time"],
                         author=author)
        self._mandatory_columns = mandatory_columns

    @property
    def events(self):
        """
        Retrieve the unique event IDs present in the data.

        Returns:
        --------
        list
            A list of unique event IDs.
        """
        return list(set(self.data["ev_id"]))

    def __str__(self) -> str:
        """
        String representation of the Picks class.

        Returns:
        --------
        str
            A summary of the number of events and picks in the data.
        """
        msg = f"Picks | {self.__len__()} picks, ({len(self.events)} events-{len(self.stations)} stations)"
        return msg

    @property
    def phase_hints(self):
        """
        Retrieve unique phase hints from the data.

        Returns:
        --------
        list
            A list of unique phase hints.
        """
        return list(set(self.data["phase_hint"]))
    
    @property
    def P_counts(self):
        """
        Count the number of P-phase picks in the data.

        Returns:
        --------
        int
            The number of P-phase picks.
        """
        return len(self.data[self.data["phase_hint"].str.contains("P", case=False)])
    
    @property
    def S_counts(self):
        """
        Count the number of S-phase picks in the data.

        Returns:
        --------
        int
            The number of S-phase picks.
        """
        return len(self.data[self.data["phase_hint"].str.contains("S", case=False)])

    @property
    def lead_pick(self):
        """
        Get the pick with the earliest arrival time.

        Returns:
        --------
        pd.Series
            The row corresponding to the earliest pick.
        """
        min_idx = self.data['time'].idxmin()  # Get the index of the earliest pick time.
        row = self.data.loc[min_idx, :]  # Retrieve the row at that index.
        return row

    @property
    def stations(self):
        """
        Retrieve unique station IDs from the data.

        Returns:
        --------
        list
            A list of unique station IDs in the format 'network.station'.
        """
        data = self.data.copy()
        data = data.drop_duplicates(subset=["network", "station"], ignore_index=True)
        data["station_ids"] = data.apply(lambda x: ".".join((x.network, x.station)), axis=1)
        return data["station_ids"].to_list()

    def drop_picks_with_single_phase(self):
        """
        Drop picks that have only one phase (e.g., only P or only S) for each event-station pair.

        Returns:
        --------
        Picks
            The updated Picks instance with only picks having both P and S phases.
        """
        if self.data.empty:
            return self

        data = self.data.copy()
        picks = []
        
        # Group data by event ID and station, and filter for stations with both P and S phases
        for _, df in data.groupby(["ev_id", "station"]):
            df = df.drop_duplicates(["phase_hint"])  # Remove duplicate phases
            if len(df) == 2:  # Keep only groups with both P and S phases
                picks.append(df)
        
        if not picks:  # If no valid picks are found, set an empty DataFrame
            picks = pd.DataFrame()
        else:
            picks = pd.concat(picks, axis=0)  # Combine all valid picks
            # picks.reset_index(inplace=True, drop=True)
        
        self.data = picks
        return self
    
    def split_by_event(self):
        """
        Split the pick data into separate Picks objects for each event.
        
        Returns:
        --------
        list
            A list of Picks objects, each containing picks for a single event.
        """
        return [self.__class__(df,author=self.author) for _, df in self.data.groupby("ev_id")]
        
    def add_artificial_picks(self, events, distances, phase_type=None, distance_label=None):
        """
        Add artificial picks to the seismic dataset by performing linear regression on existing picks.
        
        Parameters:
        -----------
        events : Events class
            A class containing seismic event data with origin times.
        distances : list
            A list of distances at which artificial picks should be added.
        phase_type : str or list, optional
            The phase types to consider (e.g., "P" or "S"). If None, defaults to ["P", "S"].
        distance_label : str, optional
            The column name for distance values. Defaults to "utdq_distance".
        """
        if distance_label is None:
            distance_label = "utdq_distance"
        
        if phase_type is None:
            phase_type = ["P", "S"]
        elif isinstance(phase_type, str):
            phase_type = [phase_type]
        elif not isinstance(phase_type, list):
            raise ValueError("phase_type must be a string or list of strings")

        max_index = self.data.index.max()
        if max_index is None:
            max_index = 0
        else:
            max_index += 1

        # Iterate through each group of events based on event ID and phase type
        for (ev_id, phase), group in self.data.groupby(["ev_id", "phase_hint"]):
            if phase not in phase_type:
                continue
            
            group.dropna(subset=[distance_label], inplace=True)  # Remove NaN distances
            if len(group) > 1:  # Linear regression requires at least two points
                group = group.sort_values("time")
                
                # Retrieve the origin time for the event
                origin_time = events.data[events.data["ev_id"] == ev_id]["origin_time"].values[0]
                
                # Compute travel times
                group["travel_time"] = group["time"].apply(lambda x: (x - origin_time).total_seconds())
                
                # Perform linear regression between distance and travel time
                length = len(group)
                slope, intercept, r_value, _, _ = linregress(group[distance_label], group["travel_time"])
                
                # Generate artificial picks based on regression results
                for i,distance in enumerate(distances):
                    if distance < 0:
                        continue  # Ignore negative distances
                    
                    travel_time = pd.Timedelta(seconds=distance * slope) + pd.Timedelta(seconds=intercept)
                    time = origin_time + travel_time
                    
                    random_az = random.uniform(0, 360) 
                    random_baz = (random_az + 180) % 360
                    
                    
                    artificial_pick = {
                        "ev_id": ev_id,
                        "pick_id": f"{phase}_UTDQ_utdq_{i}_{time.strftime('%Y%m%dT%H%M%S.%f')}",  # Unique pick ID
                        # "pick_id": x['phase_hint']}_{x['network']}_{x['station']}_{x['time']}
                        "network":"UTDQ",
                        "station":f"UTDQ_{i}",
                        "time": time,
                        "phase_hint": phase,
                        "author": "utdquake",
                        "utdq_time": travel_time.total_seconds(),
                        "utdq_real": True,
                        f"{distance_label}": distance,
                        "utdq_azimuth": random_az,
                        "utdq_bazimuth": random_baz,
                        "utdq_r2": r_value,
                        "utdq_r2_length": length
                    }
                    self.data["utdq_r2"] = 1
                    self.data["utdq_r2_length"] = length
                    artificial_pick = pd.DataFrame([artificial_pick],index=[max_index])
                    max_index += 1
                    
                    # self.data = pd.concat([self.data, artificial_pick], ignore_index=True)
                    self.data = pd.concat([self.data, artificial_pick], ignore_index=False)

    def remove_phases_randomly(
        self, 
        keep_ratio_p: float = 0.5, 
        keep_ratio_s: float = 0.3, 
        min_p: int = 4, 
        min_s: int = 2, 
        distance_label: Optional[str] = None
    ) -> None:
        """
        Randomly removes seismic phases for each event, while ensuring that 
        at least a minimum number of 'P' and 'S' phases are kept.

        Parameters:
        - keep_ratio_p (float): The proportion of P phases to keep based on their probability (0 < keep_ratio <= 1).
        - keep_ratio_s (float): The proportion of S phases to keep based on their probability (0 < keep_ratio <= 1).
        - min_p (int): The minimum number of 'P' phases to keep for each event (must be >= 0).
        - min_s (int): The minimum number of 'S' phases to keep for each event (must be >= 0).
        - distance_label (str, optional): The column name for distance values. Defaults to "utdq_distance".

        Modifies:
        - self.data (pd.DataFrame): The DataFrame containing seismic phase data is updated with the
        selected phases for each event.
        """
        
        def phase_removal(event_df: pd.DataFrame) -> pd.DataFrame:
            """
            Removes seismic phases for a specific event, keeping at least a minimum 
            number of 'P' and 'S' phases based on weighted random selection favoring 
            closer stations.

            Parameters:
            ----------
            event_df : pd.DataFrame
                DataFrame containing the seismic phases for a specific event. 
                Must include 'phase_hint' and distance columns.

            Returns:
            -------
            pd.DataFrame
                A DataFrame containing the selected phases after applying the removal criteria.
            """
            # Separate phases by type: 'P' for Primary, 'S' for Secondary
            p_phases = event_df[event_df['phase_hint'] == 'P'].copy()
            s_phases = event_df[event_df['phase_hint'] == 'S'].copy()

            def calculate_weights(df: pd.DataFrame) -> tuple:
                """
                Calculate normalized probability weights based on distance.
                Closer phases get higher weights.

                Parameters:
                ----------
                df : pd.DataFrame
                    DataFrame containing phases.

                Returns:
                -------
                tuple
                    - Sorted DataFrame by distance.
                    - Normalized probability weights as a Series.
                """
                if df.empty:
                    return df, pd.Series(dtype=float)

                sorted_df = df.sort_values(distance_label)
                weights = 1 / (sorted_df[distance_label] + 1e-6)  # Avoid division by zero
                weights = weights / weights.sum()  # Normalize weights
                return sorted_df, weights

            # Calculate weights for P and S phases
            p_phases, p_weights = calculate_weights(p_phases)
            s_phases, s_weights = calculate_weights(s_phases)

            # Validate distance values (no NaNs allowed)
            if not p_phases.empty and p_phases["utdq_distance"].isna().any():
                bad = p_phases[p_phases["utdq_distance"].isna()]
                print(bad)
                raise ValueError(
                    f"P phases have NaN utdq_distances. Check your stations file and "
                    f"confirm the stations {set(bad['station'].to_list())} are there."
                )

            if not s_phases.empty and s_phases["utdq_distance"].isna().any():
                bad = s_phases[s_phases["utdq_distance"].isna()]
                print(bad)
                raise ValueError(
                    f"S phases have NaN utdq_distances. Check your stations file and "
                    f"confirm the stations {set(bad['station'].to_list())} are there."
                )

            # Initialize selected indices
            selected_indices = set()

            # Randomly select P phases
            p_keep = np.array([], dtype=int)
            if not p_phases.empty:
                n_p = max(int(len(p_phases) * keep_ratio_p), min_p)
                n_p = min(n_p, len(p_phases))  # Cannot select more than available
                p_keep = np.random.choice(
                    p_phases.index,
                    size=n_p,
                    p=p_weights if not p_weights.empty else None,
                    replace=False
                )
                selected_indices.update(p_keep)

            # Randomly select S phases
            s_keep = np.array([], dtype=int)
            if not s_phases.empty:
                n_s = max(int(len(s_phases) * keep_ratio_s), min_s)
                n_s = min(n_s, len(s_phases))
                s_keep = np.random.choice(
                    s_phases.index,
                    size=n_s,
                    p=s_weights if not s_weights.empty else None,
                    replace=False
                )
                selected_indices.update(s_keep)

            # Combine the selected phases
            keep_phases = event_df.loc[list(selected_indices)].copy()

            return keep_phases

        # Default distance label if none provided
        if distance_label is None:
            distance_label = "utdq_distance"

        # Make a copy of the data to avoid modifying the original DataFrame directly
        data: pd.DataFrame = self.data.copy()
        # Apply the phase_removal function to each event in the DataFrame
        self.data = data.groupby('ev_id').apply(phase_removal).reset_index(level="ev_id",drop=True)

    def plot(self, y=None, phase_type=None, ax=None, show=True, **kwargs):
        """
        Plot the pick data with real and artificial picks.
        
        Parameters:
        -----------
        y : str, optional
            The column to be plotted on the y-axis. Defaults to "utdq_distance".
        phase_type : str or list, optional
            The phase types to plot (e.g., "P" or "S"). If None, defaults to ["P", "S"].
        ax : matplotlib.axes.Axes, optional
            The axes object to plot on. If None, a new figure is created.
        show : bool, optional
            Whether to display the plot immediately. Defaults to True.
        **kwargs
            Additional keyword arguments for the scatter plot.
        
        Returns:
        --------
        ax : matplotlib.axes.Axes
            The axes object with the plotted data.
        """
        if y is None:
            y = "utdq_distance"
        
        if phase_type is None:
            phase_type = ["P", "S"]
        elif isinstance(phase_type, str):
            phase_type = [phase_type]
        elif not isinstance(phase_type, list):
            raise ValueError("phase_type must be a string or list of strings")
        
        if ax is None:
            fig, ax = plt.subplots()
        
        colors = {'P': 'blue', 'S': 'red'}  # Define colors for P and S phases
        
        for phase in self.data['phase_hint'].unique():
            if phase not in phase_type:
                continue
            
            subset = self.data[self.data['phase_hint'] == phase]
            
            # Normalize phase name
            if "p" in phase.lower():
                phase = "P"
            elif "s" in phase.lower():
                phase = "S"
            else:
                raise ValueError(f"Invalid phase: {phase}")
            
            artificial = subset[subset["author"] == "artificial"]
            real = subset[subset["author"] != "artificial"]
            
            # Scatter plot for real and artificial picks
            ax.scatter(real["time"], real[y], color=colors[phase], label=phase, **kwargs)
            if not artificial.empty:
                ax.scatter(artificial["time"], artificial[y], color=colors[phase], label=f"artificial {phase}", marker="x", **kwargs)
        
        ax.set_xlabel("Time")
        ax.set_ylabel(y)
        ax.legend()
        
        if show:
            plt.show()
        
        return ax
    