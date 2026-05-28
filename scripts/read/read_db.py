import pandas as pd
import sqlite3

# db_path = "/groups/igonin/ecastillo/UTDQuake/bank/ak/.index.db"
# db_path = "/home/edc240000/scratch/utdbank/.index.db"
# db_path = "/home/edc240000/scratch/utdbank/.stations/.GCI_KKFLS.db"

# db_path = "/groups/igonin/ecastillo/UTDQuake/bank/GCI/.picks.db"
# db_path = "/groups/igonin/ecastillo/UTDQuake/bank/tx/.picks.db"
db_path = "/groups/igonin/ecastillo/UTDQuake/bank/tx/.events.db"

conn = sqlite3.connect(db_path)
#print tablers
query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(query, conn)
print(tables)

query = 'SELECT * FROM "/events/index";'
picks = pd.read_sql_query(query, conn)
print(picks)
print(picks.info())


# query = 'SELECT * FROM "/stations/index";'
# stations = pd.read_sql_query(query, conn)
# print(stations)

# print(len(events))
# print(events.info())
# events.drop_duplicates(subset=,inplace=True)
# print(events)

# query = 'SELECT * FROM "/events/index";'
# events = pd.read_sql_query(query, conn)
# print(events)

#print stations table
# query = 'SELECT * FROM "/stations/index";'
# stations = pd.read_sql_query(query, conn)
# print(stations)