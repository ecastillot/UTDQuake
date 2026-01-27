import sqlite3
import pandas as pd
from datetime import datetime
# from utdquake.plot import compare_latlon

# db_path = "/groups/igonin/ecastillo/Bank/stations/.stations.db"
db_path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/JAPAN/.index.db"
# db_path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/events/.stations/.2T_EF51.db"
# table_names = get_table_names(path)
# print(table_names)

conn = sqlite3.connect(db_path)
# Create a cursor object
cursor = conn.cursor()

# Show all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)
exit()
# # Read data from a specific table
cursor.execute("SELECT * FROM '/stations/last_updated';")
rows = cursor.fetchall()

# for row in rows:
#     print(row)

# for row in rows:
#     ts = row[0]
#     print(datetime.utcfromtimestamp(ts))

df = pd.read_sql_query("SELECT * FROM '/stations/index'", conn)


png_path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/tx/latlon_comparison.png"
compare_latlon(df, png_path, to_km=True, dpi=300)

print(df.info())
# print(df.info())
# print(df[["calculated_latitude","calculated_longitude","confirmed_latitude","confirmed_longitude"]])

# df = pd.read_sql_query("SELECT * FROM 'stations_index'", conn)
# print(df.info())