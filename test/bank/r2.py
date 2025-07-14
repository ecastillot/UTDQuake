import sqlite3
import pandas as pd

# Query stations
path = "/groups/igonin/Bank/events/tx/.index.db"
conn = sqlite3.connect(path)
station_class = "gd"
query = f"""
        SELECT *
        FROM "/stations/{station_class}"
        WHERE rowid IN (
                SELECT MIN(rowid)
                FROM "/stations/{station_class}"
                GROUP BY network, station
        )
        """
tables = pd.read_sql_query(query, conn)
tables = tables[["network","station","longitude","latitude","elevation"]]
print(tables.info())
exit()

# Query summary
path = "/groups/igonin/Bank/events/tx/.index.db"
conn = sqlite3.connect(path)
query = 'SELECT * FROM "/events/summary"'
tables = pd.read_sql_query(query, conn)
print(tables.info())
exit()

# Query events
path = "/groups/igonin/Bank/events/tx/.index.db"
conn = sqlite3.connect(path)
query = 'SELECT * FROM "/events/index"'
tables = pd.read_sql_query(query, conn)
print(tables.info())
exit()

# Query tables
path = "/groups/igonin/Bank/events/tx/.index.db"
conn = sqlite3.connect(path)
query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(query, conn)
print(tables)

exit()

# path = "/groups/igonin/PHASED/events/.index.db"
# conn = sqlite3.connect(path)
# # query = "SELECT name FROM sqlite_master WHERE type='table';"
# # tables = pd.read_sql_query(query, conn)
# # print(tables)

# df = pd.read_sql_query('SELECT * FROM "/events/index"', conn)
# print(df)
# exit()

#stations

# path = "/groups/igonin/Bank/events/tx/.stats/summary.db"
path = "/groups/igonin/Bank/events/tx/.index.db"
conn = sqlite3.connect(path)
query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(query, conn)
print(tables)


station_class = "gd"
stations_query = f"""
                    SELECT *
                    FROM "/stations/{station_class}"
                    WHERE rowid IN (
                            SELECT MIN(rowid)
                            FROM "/stations/{station_class}"
                            GROUP BY network, station
                    )
                    """
df = pd.read_sql_query(stations_query, conn)
# df["location"] = df["location"].astype(str).str.zfill(2)
print(df.info())
print(df)

summary = pd.read_sql_query('SELECT * FROM "/events/summary"', conn)
print(summary.info())
print(summary)