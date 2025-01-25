import pandas as pd
from utdquake.core.event.data import DataFrameHelper,MulDataFrameHelper
from utdquake.core.database.database import load_dataframe_from_sqlite
from utdquake.core.event.events import Events

ev_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/origin.csv"
ev = pd.read_csv(ev_path)
events = Events(ev,xy_epsg="EPSG:3116",author="X")
picks_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/picks.db"
picks = events.get_picks(picks_path=picks_path,author="manual")
print(picks.data)
# events.filter_by_r_az(latitude=35,longitude=-96,r=150)
# print(events.data)
# events.filter_rectangular_region([-103.5,-103,30.8,31.5])
# print(events.__str__(True))
# print(events.data)