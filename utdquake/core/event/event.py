# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-01-23 22:36:58
#  * @modify date 2025-01-23 22:36:58
#  * @desc [description]
#  */

from .data import DataFrameHelper
import pandas as pd

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
    
    def __init__(self, data, author=None) -> None:
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
        super().__init__(data=data, required_columns=mandatory_columns)
        self.author = author
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
        msg = f"Picks | {len(self.events)} events, {self.__len__()} picks"
        return msg

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
            picks.reset_index(inplace=True, drop=True)
        
        self.data = picks
        return self
            

# parse_coords (dict, optional): Dictionary specifying latitude, longitude, and EPSG for parsing coordinates.
#             Example: {'latitude': 'float', 'longitude': 'float', 'xy_epsg': (str)}. Defaults to None.
# Parse coordinates, if specified
# if parse_coords is not None:
#     if not isinstance(parse_coords, dict):
#         raise Exception(
#             "The 'parse_coords' parameter must be a dictionary with the following items: "
#             "'latitude': 'float', 'longitude': 'float', 'xy_epsg': (str)"
#         )
    
#     # Required keys for coordinate parsing
#     req_keys = ["latitude", "longitude", "xy_epsg"]
#     for key in req_keys:
#         if key not in data.columns:
#             raise Exception(f"The column '{key}' is required for parsing coordinates.")