from utdquake.bank.bank import UTDQBank
import obsplus
import pandas as pd
import sqlite3
import os
# bank = EventBank("/groups/igonin/ecastillo/UTDQuake/bank/ak")

path = "/groups/igonin/ecastillo/UTDQuake/bank/GCI"
ebank = UTDQBank(base_path=path,
                path_structure='{year}/{month}/{day}',
                name_structure='{event_id_end}',
                format='quakeml')
folder_path = "/groups/igonin/ecastillo/DAS_uw_data/GCI_QuakeML_Picks_16042026/04012026"
print(ebank)


db_path = os.path.join(path,".index.db")
conn = sqlite3.connect(db_path)
query = 'SELECT * FROM "/events/index";'
events = pd.read_sql_query(query, conn)

id_0 = events.loc[0,"event_id"]
picks = ebank.get_picks(event_ids=[id_0 ])
print(picks)

print(picks.info())