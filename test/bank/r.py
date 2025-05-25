import sqlite3
import pandas as pd


# path = "/groups/igonin/utdquake/bank/events/.index.db"
# conn = sqlite3.connect(path)
# query = "SELECT name FROM sqlite_master WHERE type='table';"
# tables = pd.read_sql_query(query, conn)
# print(tables)

# df = pd.read_sql_query('SELECT * FROM "/events/index"', conn)
# print(df)
# df = pd.read_sql_query('SELECT * FROM "/events/metadata"', conn)
# print(df)
# df = pd.read_sql_query('SELECT * FROM "/events/last_updated"', conn)
# print(df)


path = "/groups/igonin/utdquake/bank/stations/.stations.db"
conn = sqlite3.connect(path)
query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(query, conn)
print(tables)

df = pd.read_sql_query('SELECT * FROM "/stations/index"', conn)
print(df)