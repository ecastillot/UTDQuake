from utdquake.bank.bank import UTDQBank
import obsplus
import pandas as pd
import sqlite3
import os
# bank = EventBank("/groups/igonin/ecastillo/UTDQuake/bank/ak")

path = "/groups/igonin/ecastillo/UTDQuake/bank/pr"
ebank = UTDQBank(base_path=path,
                path_structure='{year}/{month}/{day}',
                name_structure='{event_id_end}',
                format='quakeml')

ebank.get_summary()