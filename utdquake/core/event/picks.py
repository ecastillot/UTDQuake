# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-01-23 22:36:58
#  * @modify date 2025-01-23 22:36:58
#  * @desc [description]
#  */

from .data import DataFrameHelper, MulDataFrameHelper
from ..database.database import load_from_sqlite,load_chunks_from_sqlite
from pandas.api.types import is_datetime64_any_dtype
import pandas as pd

def read_picks(path, author, ev_ids=None, custom_params=None, drop_duplicates=True):
    """
    Load earthquake picks from an SQLite database and return a Picks object.

    Args:
        path (str): The path to the SQLite database file containing pick data.
        author (str): The name or identifier of the author associated with the picks.
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
        Picks: A `Picks` object containing the loaded pick data and associated author information.

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
        drop_duplicates=drop_duplicates,
        sortby="time"           # Sort the data by the "time" column
    )

    # Return a Picks object with the loaded data and author information
    return Picks(picks, author)
  
def read_picks_in_chunks(path, author, chunksize=100, custom_params=None, drop_duplicates=True):
    """
    Load earthquake picks from an SQLite database in chunks and yield a Picks object for each chunk.

    Args:
        path (str): The path to the SQLite database file containing pick data.
        author (str): The name or identifier of the author associated with the picks.
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
        yield Picks(picks, author)
    
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
            
class MulPicks(MulDataFrameHelper):
    def __init__(self, picks_list=[]):
        """
        Initialize a MulPicks object, which is a collection of Picks objects.

        Parameters:
        -----------
        picks_list : list, optional
            A list of Picks objects to initialize the collection (default is an empty list).

        Raises:
        -------
        Exception
            If any item in picks_list is not an instance of Picks.
        """
        for picks in picks_list:
            if not isinstance(picks, Picks):
                raise Exception(f"{picks} must be a Picks object")

        # Call the parent class initializer with the provided picks_list
        super().__init__(datahelpers=picks_list)
        self.name = "MulPicks"
        self.picks_list = picks_list

    def __str__(self, extended=False) -> str:
        """
        String representation of the MulPicks class.

        Parameters:
        -----------
        extended : bool, optional
            Whether to include extended details for each Picks object (default is False).

        Returns:
        --------
        str
            A formatted string summarizing the collection and optionally detailed descriptions.
        """
        # Use the helper method from the parent class to generate the string
        return self._get_str(extended=extended, object_name=self.name)

    def get_stations(self, preferred_author=None):
        """
        Retrieve a list of unique station IDs from the Picks objects in the picks_list.

        Parameters:
        -----------
        preferred_author : str, optional
            Filter the Picks objects by the specified author (default is None, meaning no filtering).

        Returns:
        --------
        list
            A list of unique station IDs.

        Raises:
        -------
        Exception
            If no station IDs are found, either because the picks_list is empty or the preferred_author filter excludes all entries.
        """
        station_ids = []

        # Iterate through each Picks object in the picks_list
        for picks in self.picks_list:
            # If a preferred author is specified, skip Picks objects from other authors
            if preferred_author is not None:
                if picks.author != preferred_author:
                    continue
            # Add the stations from the current Picks object to the station_ids list
            station_ids += picks.stations

        # Raise an exception if no station IDs are found
        if not station_ids:
            raise Exception("Empty station IDs. Review your preferred author in case you are using it.")

        # Remove duplicates from the station_ids list
        station_ids = list(set(station_ids))
        return station_ids

    def get_lead_pick(self, preferred_author=None):
        """
        Retrieve the station and time of the lead pick (earliest pick time) from the Picks objects.

        Parameters:
        -----------
        preferred_author : str, optional
            Filter the Picks objects by the specified author (default is None, meaning no filtering).

        Returns:
        --------
        tuple
            A tuple containing the station ID (str) and the time (datetime) of the lead pick.

        Raises:
        -------
        Exception
            If the picks_list is empty or no picks match the preferred_author.
        """
        lead_pick = []

        # Iterate through each Picks object in the picks_list
        for picks in self.picks_list:
            # If a preferred author is specified, skip Picks objects from other authors
            if preferred_author is not None:
                if picks.author != preferred_author:
                    continue
            # Append the lead pick (station and time) from the current Picks object
            lead_pick.append(picks.lead_pick)

        # Convert the list of lead picks to a DataFrame for easy processing
        lead_pick = pd.DataFrame(lead_pick, columns=["station", "time"])

        # Get the index of the minimum arrival time (earliest pick)
        min_idx = lead_pick['time'].idxmin()

        # Retrieve the row corresponding to the earliest pick
        row = lead_pick.loc[min_idx, ['time', 'station']]

        # Return the station and time of the lead pick as a tuple
        return row.station, row.time
    
    def drop_picks_with_single_phase(self):

        all_picks = []

        # Iterate through each Picks object in the picks_list
        for picks in self.picks_list:
            picks.drop_picks_with_single_phase()
            all_picks.append(picks) 
        
        return self.__class__(picks_list=all_picks)
    
    def compare_times(self, author1, author2):
        """
        Compare the time column between Picks objects from two different authors.

        Parameters:
        -----------
        author1 : str
            The name of the first author to compare.
        author2 : str
            The name of the second author to compare.

        Returns:
        --------
        pd.DataFrame
            A DataFrame with merged data, including the time difference between the two authors.

        Raises:
        -------
        Exception
            If more than one Picks object exists for the same author.
            If the time column is not of datetime type.
        """
        # Retrieve Picks objects for the given authors
        dfh1_list = self[author1]
        dfh2_list = self[author2]
        key = "time"

        # Initialize a list to store data from both authors
        all_data = []
        for dfh_list in [dfh1_list, dfh2_list]:
            # Ensure only one Picks object exists for the author
            if len(dfh_list) > 1:
                raise Exception(f"More than 1 {self.single_name} with the same author {dfh_list[0].author}")

            # Retrieve the data and check the time column type
            dfh = dfh_list[0]
            data = dfh.data
            time_type = data[key].dtype

            if not is_datetime64_any_dtype(data[key]):
                raise Exception(f"Error: {key} column in {self.single_name}[{dfh.author}] is a {time_type}. It must be a datetime object")

            # Append the data for merging
            all_data.append(data)

        # Define columns to merge on, excluding the time key
        cols2merge = self.required_columns
        suffixes = list(map(lambda x: "_" + x, [author1, author2]))
        cols2merge.remove(key)

        # Merge the data from the two authors
        data = pd.merge(
            left=all_data[0],
            right=all_data[1],
            on=cols2merge,
            suffixes=suffixes
        )

        # Calculate the time difference in seconds
        data.loc[:, f"delta_{key}"] = data[key + suffixes[0]] - data[key + suffixes[1]]
        data[f"delta_{key}"] = data[f"delta_{key}"].dt.total_seconds()

        # Select final columns for the output DataFrame
        final_cols = cols2merge + [key + suffixes[0]] + [key + suffixes[1]] + [f"delta_{key}"]
        data = data[final_cols]

        return data

        
        
        
        # list2compare = [author1,author2]
        
        # if sr_columns is None:
        #     sr_columns = ["time"]
        
        # data2compare = []
        # for pick in self.__iter__():
        #     if pick.author in list2compare:
        #         data = pick.data.copy()
        #         _mandatory_columns = pick.required_columns
                
        #         _optional_columns = [v for v in sr_columns\
        #                     if v in data.columns.to_list()]
                
        #         if _optional_columns:
        #             cols = _mandatory_columns + _optional_columns
        #         else:
        #             cols = _mandatory_columns
                
        #         data = data[cols]
        #         data2compare.append(data)
                
        # key = "time"
        # cols2merge =  _mandatory_columns.copy() 
        # cols2merge.remove(key)
        # suffixes = list(map(lambda x: "_"+x,list2compare))
        
        # # print(data2compare[0],data2compare[1],cols2merge,suffixes)
        # data = pd.merge(left=data2compare[0], 
        #                 right=data2compare[1],
        #                 on=cols2merge,
        #                 suffixes=suffixes )
        # print(data2compare[0].info())
        # exit()
        # data.loc[:,"delta_time"] = data[key+suffixes[0]] - data[key+suffixes[1]]
        # print(data)
        # data['delta_time'] = data['delta_time'].dt.total_seconds()
        
        # return data
    