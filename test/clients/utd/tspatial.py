import pandas as pd
from utdquake.core.event.data import DataFrameHelper,MulDataFrameHelper
from utdquake.core.database import load_dataframe_from_sqlite
from utdquake.core.event.spatial import Points,SinglePoint

sta_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/stations.csv"
sta = pd.read_csv(sta_path)

p1= SinglePoint(latitude=31.18697,longitude=-103.2694,
                xy_epsg="EPSG:3116",depth=2)
p2= SinglePoint(latitude=31.61979,longitude=-104.01776,
                xy_epsg="EPSG:3116",depth=2)
stations = Points(sta,author="OK",xy_epsg="EPSG:3116")
# stations.project(p1,p2)
print(stations)
