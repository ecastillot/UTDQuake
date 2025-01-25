import pandas as pd
from utdquake.core.event.data import DataFrameHelper,MulDataFrameHelper
from utdquake.core.database import load_dataframe_from_sqlite
from utdquake.core.event.stations import Stations

sta_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/stations.csv"
sta = pd.read_csv(sta_path)
stations = Stations(sta,xy_epsg="EPSG:3116",author="X")
print(stations.data)
stations.filter_rectangular_region([-103.5,-103,30.8,31.5])
print(stations.data)