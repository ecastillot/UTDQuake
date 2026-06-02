
import os
import sqlite3
import shutil
import glob
import pandas as pd



#task 1: STATIONS: mov .stations fodler to ../.utdquake/db/stations/.{network}

def move_tables(src_db, dst_db, tables):
    """
    Move tables from one SQLite database to another.

    Parameters
    ----------
    src_db : str
        Path to the source database.

    dst_db : str
        Path to the destination database.

    tables : list of str
        Names of tables to move.
    """
    src_conn = sqlite3.connect(src_db)
    dst_conn = sqlite3.connect(dst_db)

    try:
        for table in tables:
            # Read table from source
            query = f'SELECT * FROM "{table}"'
            data = src_conn.execute(query).fetchall()

            # Get CREATE TABLE statement
            create_stmt = src_conn.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type='table' AND name=?
                """,
                (table,),
            ).fetchone()

            if create_stmt is None:
                raise ValueError(f"Table '{table}' not found")

            # Create table in destination
            dst_conn.execute(create_stmt[0])

            # Copy data
            if data:
                placeholders = ",".join("?" * len(data[0]))
                dst_conn.executemany(
                    f'INSERT INTO "{table}" VALUES ({placeholders})',
                    data,
                )

        dst_conn.commit()

        # Remove tables from source only after successful copy
        for table in tables:
            src_conn.execute(f'DROP TABLE "{table}"')

        src_conn.commit()

    finally:
        src_conn.close()
        dst_conn.close()

def std_db(bank_path):

    # STATIONS FOLDER
    bank_name = os.path.basename(bank_path)
    src_path = os.path.join(bank_path, ".stations",".*.db")

    utdquake_root = os.path.dirname(os.path.dirname(bank_path))
    stations_path = os.path.join(utdquake_root, ".utdquake","db","stations")


    logs_path = os.path.join(bank_path, ".logs","*.log")
    logs_dst_path = os.path.join(utdquake_root, ".utdquake","logs",bank_name,"banks")

    dst_path = os.path.join(stations_path, f".{bank_name}")

    # print(f"Source path: {src_path}")
    # print(glob.glob(src_path, recursive=True))

    #move logs
    if glob.glob(logs_path) == []:
        print(f"Logs path {logs_path} does not exist. Skipping.")
    else:
        print(f"Moving {logs_path} to {logs_dst_path}")
        os.makedirs(logs_dst_path, exist_ok=True)
        os.system(f"mv {logs_path} {logs_dst_path}")
        shutil.rmtree(os.path.dirname(logs_path))

    #move folder
    if glob.glob(src_path) == []:
        print(f"Source path {src_path} does not exist. Skipping.")
    else:
        print(f"Moving {src_path} to {dst_path}")
        os.makedirs(stations_path, exist_ok=True)
        os.system(f"mv {src_path} {dst_path}")
        
        #rm folder
        shutil.rmtree(os.path.dirname(src_path))

    src_db = os.path.join(bank_path, ".index.db")
    dst_db = os.path.join(stations_path, f"{bank_name}.db")

    if not os.path.exists(dst_db):

        print(f"Moving {src_db} to {dst_db}")


        conn = sqlite3.connect(src_db)
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql_query(query, conn)
        print(tables)

        move_tables(
                src_db=src_db,
                dst_db=dst_db,
                tables=[
                    "/stations/index",
                    "/stations/last_updated",
                ],
            )
        tables = pd.read_sql_query(query, conn)
        print(tables)

    else:
        print(f"Destination {dst_db} already exists. Skipping.")

    #STATIONS DB

# bank_path = "/groups/igonin/ecastillo/UTDQuake/bank/admin"
# bank_paths = "/groups/igonin/ecastillo/UTDQuake/bank"
bank_paths = "/groups/igonin/ecastillo/UTDQuake_DAS/bank"

for bank_name in os.listdir(bank_paths):
    bank_path = os.path.join(bank_paths, bank_name)
    std_db(bank_path)
    # print(bank_path)


# std_db(bank_path)
