import sqlite3
import pandas as pd
import datetime as dt

def save_dataframe_to_sqlite(df, db_path, table_name):
    """
    Save a DataFrame to an SQLite database, appending data if the table exists.

    Args:
        df (pd.DataFrame): The DataFrame to be saved.
        db_path (str): The path to the SQLite database file.
        table_name (str): The name of the table in the SQLite database.

    Notes:
        - If the table already exists in the database, new data will be appended.
        - The DataFrame's index will not be saved to the database.
    """
    with sqlite3.connect(db_path) as conn:
        # Save the DataFrame to the SQLite database
        # If the table exists, new rows are appended; otherwise, a new table is created
        df.to_sql(table_name, conn, if_exists='append', index=False)

def load_dataframe_from_sqlite(db_path, tables=None, custom_params=None, parse_dates=None,
                               drop_duplicates=True, sortby=None):
    """
    Load a DataFrame from an SQLite database based on optional query parameters.

    Args:
        db_path (str): The path to the SQLite database file.
        tables (list of str, optional): List of table names to load data from. 
            If None, load data from all tables. Defaults to None.
        custom_params (dict, optional): Custom filtering parameters for the query. 
            Expected format: {column_name: {'value': value, 'condition': condition}}.
            For example in case of picks database: To limit the search to 0.5 degrees of distance and stations started with OKAS. 
            custom_params={"distance":{"condition":"<","value":0.5},
                                "station":{"condition":"LIKE","value":"OKAS%"}
                                  }.
            Defaults to None.
        parse_dates (list of str, optional): List of columns to parse as datetime. Defaults to None.
        drop_duplicates (bool, optional): Whether to drop duplicate rows. Defaults to True.
        sortby (str, optional): Column name to sort the resulting DataFrame by. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing data from the specified table(s) and filtered 
            based on custom parameters.

    Raises:
        Exception: If `custom_params` does not follow the required structure.

    Notes:
        - If no tables are specified, all tables in the database are queried.
        - The DataFrame is sorted by the specified column (`sortby`) if provided.
        - If `drop_duplicates` is True, duplicates are removed based on `custom_params` keys.
    """
    # Connect to the SQLite database
    with sqlite3.connect(db_path) as conn:
        # Query to retrieve all table names in the database
        tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        all_tables = pd.read_sql_query(tables_query, conn)['name'].tolist()

        # If no specific tables are provided, use all tables
        if tables is None:
            tables = all_tables
        else:
            # Intersect provided tables with available tables
            tables = list(set(tables).intersection(all_tables))
            complement = list(set(all_tables).difference(tables))
            
            if len(complement) > 0:
                print(f"Warning: {len(complement)} tables found.")

        # Initialize a list to store DataFrames from each table
        all_dataframes = []

        for table in tables:
            try:
                # Get column information for the current table
                cursor = conn.execute(f"PRAGMA table_info({table})")
            except sqlite3.OperationalError:
                print(f"Table '{table}' not found in the database.")
                continue

            # Extract column names from the table
            columns = [col[1] for col in cursor.fetchall()]

            # Build the query to fetch data from the current table
            query = f"SELECT * FROM {table} WHERE 1=1"
            sql_params = {}
            req_keys = ["value", "condition"]

            # Add custom filtering parameters to the query
            if custom_params is not None:
                for key, info in custom_params.items():
                    # Validate the structure of custom_params
                    for req_key in req_keys:
                        if req_key not in list(info.keys()):
                            raise Exception(
                                "custom_params argument requires this structure: "
                                "{x: {'value': y, 'condition': y}}"
                            )

                    # Add the filter to the query if the column exists in the table
                    if key in columns:
                        query += f" AND {key} {info['condition']} :{key}"
                        value = info["value"]

                        # Format datetime values as strings
                        if isinstance(value, dt.datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')

                        sql_params[key] = value

            # Execute the query and load data into a DataFrame
            df = pd.read_sql_query(query, conn, params=sql_params, parse_dates=parse_dates)

            # Remove duplicate rows if required
            if drop_duplicates:
                if custom_params:
                    drop_subset = list(custom_params.keys())
                else:
                    drop_subset = None
                
                df = df.drop_duplicates(subset=drop_subset, ignore_index=True)

            # Sort the DataFrame by the specified column if provided
            if sortby:
                df = df.sort_values(by=sortby, ignore_index=True)

            # Append the DataFrame to the list
            all_dataframes.append(df)

        # Combine all DataFrames into a single DataFrame
        if all_dataframes:
            df = pd.concat(all_dataframes, ignore_index=True)
        else:
            df = pd.DataFrame()

    # Return the resulting DataFrame
    return df

if __name__ == "__main__":
    path = "/home/emmanuel/ecastillo/dev/delaware/data/metadata/delaware_database/TX.PB5.00.CH_ENZ.db"
    # path = "/home/emmanuel/ecastillo/dev/delaware/data/metadata/delaware_database/4O.WB10.00.HH_ENZ.db"
    df = load_dataframe_from_sqlite(path, "availability", 
                                    starttime="2024-01-01 00:00:00", 
                                    endtime="2024-08-01 00:00:00")
    print(df)
    
    import sqlite3

    # def list_tables(db_path):
    #     """List all tables in the SQLite database."""
    #     with sqlite3.connect(db_path) as conn:
    #         cursor = conn.cursor()
    #         cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    #         tables = cursor.fetchall()
    #         print(tables)
    #         for table in tables:
    #             print(table[0])

    # # Example usage
    # list_tables(path)