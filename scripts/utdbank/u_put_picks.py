from utdquake.bank.bank import UTDQBank
import obsplus
import pandas as pd
import sqlite3
import os

import logging

logging.basicConfig(level=logging.INFO)

# bank = EventBank("/groups/igonin/ecastillo/UTDQuake/bank/ak")

path = "/groups/igonin/ecastillo/UTDQuake/bank/tx"
ebank = UTDQBank(base_path=path,
                path_structure='{year}/{month}/{day}',
                name_structure='{event_id_end}',
                format='quakeml')
# print(ebank)
# print(ebank.read_index()[["event_id"]])

# ev_id = "smi:org.gfz-potsdam.de/geofon/tx2025oxvijj"
ev_id = ebank.read_index()[["event_id"]].loc[0:10,"event_id"].to_list()
# print(ev_id)

# picks = ebank.get_picks(event_ids=[ev_id])
# print(picks)

# catalog = ebank.get_events(event_id=[ev_id])
# print(catalog.utdq_events_to_df().info())
# print(catalog.utdq_picks_to_df().info())
# print(catalog)

ebank.put_picks(chunk_size=100,
            apply_utdq_qc=True,
            event_id=ev_id,
            )


# folder_path = "/groups/igonin/ecastillo/DAS_uw_data/GCI_QuakeML_Picks_16042026/04012026"
# db_path = os.path.join(path,".index.db")
# conn = sqlite3.connect(db_path)
# query = 'SELECT * FROM "/events/index";'
# events = pd.read_sql_query(query, conn)

# id_0 = events.loc[0,"event_id"]
# picks = ebank.get_picks(event_ids=[id_0 ])
# print(picks)

# print(picks.info())