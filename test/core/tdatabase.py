import pandas as pd
from utdquake.core.database.database import load_dataframe_from_sqlite
import datetime as dt

picks_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/picks.db"

starttime = dt.datetime(2024,4,19,16)
endtime = dt.datetime(2024,4,19,21)

custom_params = {"time":{"condition":">","value":starttime},
                 "azimuth":{"condition":">=","value":0},
                 "azimuth":{"condition":"<","value":180},
                 "phase_hint":{"condition":"==","value":"P"},
                 }

df = load_dataframe_from_sqlite(picks_path, parse_dates=["time"],
                                custom_params=custom_params)
print(df.info())