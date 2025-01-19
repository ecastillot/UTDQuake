import sqlite3
import pandas as pd

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

def load_dataframe_from_sqlite(db_path, tables=None, starttime=None, endtime=None):
    """
    Load a DataFrame from an SQLite database based on optional query parameters.

    Args:
        db_path (str): The path to the SQLite database file.
        tables (list of str, optional): List of table names to load data from. If None, load data from all tables. Defaults to None.
        starttime (str, optional): The start time for the data query in 'YYYY-MM-DD HH:MM:SS' format. Defaults to None.
        endtime (str, optional): The end time for the data query in 'YYYY-MM-DD HH:MM:SS' format. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame containing data from the specified table(s) and time range.

    Notes:
        - The `starttime` and `endtime` parameters are optional. The query will only filter by these fields if they exist in the table(s) and are provided.
        - The 'starttime' and 'endtime' columns in the DataFrame are converted to datetime objects if they exist.
        - The DataFrame is sorted by 'starttime' after loading if the column exists.
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
            print(f"{len(complement)} tables not found:")

        # Initialize a list to store DataFrames from each table
        all_dataframes = []

        for table in tables:
            try:
                # Get column information for the current table
                cursor = conn.execute(f"PRAGMA table_info({table})")
            except sqlite3.OperationalError:
                print(f"Table '{table}' not found in the database.")
                continue

            columns = [col[1] for col in cursor.fetchall()]

            # Build the query to fetch data from the current table
            query = f"SELECT * FROM {table} WHERE 1=1"
            params = []

            # Add starttime filter if applicable
            if 'starttime' in columns and starttime:
                query += " AND starttime >= ?"
                params.append(starttime)

            # Add endtime filter if applicable
            if 'endtime' in columns and endtime:
                query += " AND endtime <= ?"
                params.append(endtime)

            # Execute the query and load data into a DataFrame
            df = pd.read_sql_query(query, conn, params=params)
            
            # Convert 'starttime' and 'endtime' to datetime if they exist
            if 'starttime' in df.columns:
                df['starttime'] = pd.to_datetime(df['starttime'])
            if 'endtime' in df.columns:
                df['endtime'] = pd.to_datetime(df['endtime'])

            # Remove duplicate rows based on 'starttime' and 'endtime'
            drop_subset = [col for col in ['starttime', 'endtime'] if col in df.columns]
            if drop_subset:
                df = df.drop_duplicates(subset=drop_subset, ignore_index=True)

            # Sort the DataFrame by 'starttime' if the column exists
            if 'starttime' in df.columns:
                df = df.sort_values(by=['starttime'], ignore_index=True)

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