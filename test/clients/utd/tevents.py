import pandas as pd
from utdquake.core.event.events import Events
from utdquake.core.event.stations import Stations
import datetime as dt
import numpy as np

stations_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/stations.csv"
stations = pd.read_csv(stations_path)
stations = Stations(stations,xy_epsg="EPSG:3116",author="TexNet")


ev_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/origin.csv"
ev = pd.read_csv(ev_path)
events = Events(ev,xy_epsg="EPSG:3116",author="X")
picks_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/picks.db"
picks = events.get_picks(picks_path=picks_path,author="manual",
                         stations=stations)
picks.dropna(subset=["utdq_distance"])

print(picks)
print(picks.data)

picks.remove_phases_randomly()
print(picks)
print(picks.data)
# print(picks.data)
distances = np.arange(0,60,2)
picks.add_artificial_picks(events=events,
                           distances=distances,
                           phase_type=["P"])
# print(picks.data)
picks.plot()
# interp = picks._get_phase_interpolations(events)

# print(interp)

# distance = 1.023955
# distance = 0.111257
# # start,slope,intercept,r_value = phase_interp[("tx2024xoub","P")]
# start,slope,intercept,r_value = interp[("tx2024xoub","P")]
# time = pd.Timestamp(start) + dt.timedelta(seconds=distance*slope)  +dt.timedelta(seconds=intercept) 
# # print(distance,time)


# print(slope,intercept,r_value)
# print(interp)
# print(picks.data[["distance","time"]])
# print(picks.data)



# events.filter_by_r_az(latitude=35,longitude=-96,r=150)
# print(events.data)
# events.filter_rectangular_region([-103.5,-103,30.8,31.5])
# print(events.__str__(True))
# print(events.data)