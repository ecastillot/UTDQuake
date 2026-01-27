import os
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

# from utdquake.core.utdquake import UTDQuake,concatenate_index_dbs
import sqlite3

conn = sqlite3.connect("/groups/igonin/ecastillo/UTDQuake/events/ak/.picks.db")
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
print([r[0] for r in cursor.fetchall()])




# utdq = UTDQuake()
# print(utdq)
# index = utdq.build_global()
# print(index)


# import sqlite3
# conn = sqlite3.connect("/groups/igonin/ecastillo/UTDQuake/events/ak/.index.db")
# cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
# print([row[0] for row in cursor.fetchall()])