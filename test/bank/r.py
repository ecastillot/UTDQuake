import sqlite3
import pandas as pd


# path = "/groups/igonin/utdquake/bank/events/.index.db"
# conn = sqlite3.connect(path)
# # query = "SELECT name FROM sqlite_master WHERE type='table';"
# # tables = pd.read_sql_query(query, conn)
# # print(tables)

# df = pd.read_sql_query('SELECT * FROM "/events/index"', conn)
# print(df)
# # df = pd.read_sql_query('SELECT * FROM "/events/metadata"', conn)
# # print(df)
# # df = pd.read_sql_query('SELECT * FROM "/events/last_updated"', conn)
# # print(df)

# exit()

#stations

path = "/groups/igonin/utdquake/bank2/stations/.stations.db"
conn = sqlite3.connect(path)
query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(query, conn)
print(tables)

df = pd.read_sql_query('SELECT * FROM "stations_index"', conn)
df["location"] = df["location"].astype(str).str.zfill(2)
print(df)
df = df.drop_duplicates(subset=['network', 'station', 'location', 'channel'])
print(df)