import sys
lib = None
lib = "/home/edc240000/UTDQuake"
if lib is not None:
    sys.path.append(lib)

from utdquake.core.dataset.window import EQWindow
import random
from utdquake.core.event.catalog import read_catalog
import pandas as pd
from utdquake.core.event.stations import Stations
import os 
import matplotlib.pyplot as plt
import seaborn as sns
import random

out = "/home/edc240000/UTDQuake/test/clients/utd/custom_events"

stations_path = os.path.join(out,"stations.csv")
events_path = os.path.join(out,"origin.csv")
picks_path = os.path.join(out,"picks.db")
mags_path = os.path.join(out,"mags.db")

stations_data = pd.read_csv(stations_path)
stations = Stations(stations_data,xy_epsg="EPSG:3116",author="Texas")

catalog = read_catalog(events_path=events_path,
                       xy_epsg="EPSG:3116",
                       stations_path=stations_path)

picks = catalog.get_picks(picks_path=picks_path,author="manual")
picks.add_artificial_picks(events=catalog.events,
                           distances=[random.uniform(0, 60) for _ in range(4)], #4 stations
                           phase_type=["P","S"])
picks.remove_phases_randomly(keep_ratio_p=0.8,keep_ratio_s=0.5)

eqw = EQWindow(keep_order=True)
eqw.add_picks(picks)
eqw.add_noise(stations,random_range=(1, 500))
window = eqw.get_window()

# print(window)



false = window[window["utdq_real"]==False]
false["utdq_distance"] = [random.uniform(0, 60) for _ in range(len(false))]

real_artificial = window[(window["utdq_real"]==True) & (window["author"]=="utdquake")]
real_manual = window[(window["utdq_real"]==True) & (window["author"]!="utdquake")]

fig,ax = plt.subplots()
ax.plot(false["utdq_wtime"], false["utdq_distance"], 'o',color="gray")
sns.scatterplot(data=real_artificial, x='utdq_wtime', y='utdq_distance', 
                hue='phase_hint', palette='tab10',
                marker="x",
                ax=ax)
sns.scatterplot(data=real_manual, x='utdq_wtime', y='utdq_distance', 
                hue='phase_hint', palette='tab10',ax=ax)
# ax.plot(window["utdq_wtime"], window["utdq_distance"], 'o',color="darkorange")
# plt.plot(window["utdq_wtime"], window["station"], 'o')
plt.savefig("/home/edc240000/UTDQuake/test/clients/test.png", dpi=300)
plt.show()