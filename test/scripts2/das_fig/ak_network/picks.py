import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_ak"

from pathlib import Path
import utdquake as utdq
from utdquake.bank.bank import UTDQBank
import pandas as pd
import logging
import sqlite3

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

bank_path = Path("/groups/igonin/ecastillo/UTDQuake_ak/bank/ak")
bank = UTDQBank(bank_path)
picks = bank.load_picks()
print(picks)
# print(bank.read_index())
bank.put_utdq_picks(chunk_size=50,
            apply_utdq_qc=True,
            # event_id=ev_id,
            )

# ak_index_path = "/groups/igonin/ecastillo/UTDQuake/bank/ak/.index.db"
# query = 'SELECT * FROM "/stations/index";'
# conn = sqlite3.connect(ak_index_path)
# stations = pd.read_sql_query(query, conn)
# stations.rename(columns={"confirmed_latitude":"latitude",
#                         "confirmed_longitude":"longitude",
#                         "confirmed_elevation":"elevation",
#                         }, inplace=True)
# stations  = stations[["network","station","latitude","longitude","elevation"]]
# print(stations)
# bank.put_utdq_stations(stations)