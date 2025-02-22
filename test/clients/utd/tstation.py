import pandas as pd
from utdquake.core.event.stations import Stations
from utdquake.core.event.spatial import Points


sta_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/stations.csv"
sta = pd.read_csv(sta_path)
stations = Stations(sta,xy_epsg="EPSG:3116",author="X")
# print(help(Points))
# print(help(stations))
# exit()
print(stations.data)
stations.filter_rectangular_region([-103.5,-103,30.8,31.5])
print(stations.data)