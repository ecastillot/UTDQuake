import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)


import pandas as pd
from utdquake.utils.plot import plot_seismic_overview


events_path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/plots/all_events.csv"
picks_path = "/groups/igonin/ecastillo/UTDQuake/17092025/picks.csv"
save_path = "/groups/igonin/ecastillo/UTDQuake/17092025/overview.png"
events = pd.read_csv(events_path)
picks = pd.read_csv(picks_path)

print(picks.describe())

plot_seismic_overview(events,picks,savepath=save_path)




