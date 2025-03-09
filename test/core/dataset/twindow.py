import pandas as pd
from utdquake.core.event.events import Events
from utdquake.core.event.stations import Stations
import datetime as dt
import numpy as np
from utdquake.core.dataset.window import EQWindow
import matplotlib.pyplot as plt
import random

stations_path = "/home/emmanuel/ecastillo/dev/utdquake/examples/custom_events/stations.csv"
stations = pd.read_csv(stations_path)
stations = Stations(stations,xy_epsg="EPSG:3116",author="TexNet")


ev_path = "/home/emmanuel/ecastillo/dev/utdquake/examples/custom_events/origin.csv"
ev = pd.read_csv(ev_path)
events = Events(ev,xy_epsg="EPSG:3116",author="X")
picks_path = "/home/emmanuel/ecastillo/dev/utdquake/examples/custom_events/picks.db"
picks = events.get_picks(picks_path=picks_path,author="manual",
                         stations=stations)
picks.dropna(subset=["utdq_distance"])

# print(picks.data)
picks.add_artificial_picks(events=events,
                           distances=[random.uniform(0, 60) for _ in range(10)],
                           phase_type=["P"])

picks.remove_phases_randomly(keep_ratio_p=0.8,keep_ratio_s=0.5)


# print(picks.data.info())
eqw = EQWindow()
eqw.add_picks(picks)
eqw.add_noise(stations)
window = eqw.get_window()
plt.plot(window["utdq_wtime"], window["station"], 'o')
# print(window)
# print(window.info())
plt.show()
