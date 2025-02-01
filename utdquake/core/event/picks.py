# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-01-23 22:36:58
#  * @modify date 2025-01-23 22:36:58
#  * @desc [description]
#  */

from ..database.database import load_from_sqlite,load_chunks_from_sqlite

def read_db(path, ev_ids=None, custom_params=None, drop_duplicates=True):
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

    return picks
  
def read_db_in_chunks(path, chunksize=100, custom_params=None, drop_duplicates=True):
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
    