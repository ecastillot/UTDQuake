from utdquake.bank.bank import EventBank
import obsplus
import obspy
from utdquake.utils.plot import EQWindow
import matplotlib.pyplot as plt
import pandas as pd

path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/tx"
ebank = EventBank(path)
metadata = ebank.read_index()

# Define magnitude bins (edges)
bins = [0, 1,  3, 4, 5,6]

# Compute bin centers
bin_centers = [(bins[i] + bins[i+1])/2 for i in range(len(bins)-1)]

selected_events = []

for i, center in enumerate(bin_centers):
    # Select events in this bin
    bin_events = metadata[(metadata["magnitude"] >= bins[i]) & (metadata["magnitude"] < bins[i+1])]
    
    if not bin_events.empty:
        # Pick event closest to the bin center
        event_id = bin_events.iloc[(bin_events["magnitude"] - center).abs().argmin()]["event_id"]
        selected_events.append(event_id)
    else:
        # Optional: append None if no event in bin
        selected_events.append(None)

events = selected_events
# events = events[0:3]


cat = ebank.get_events(event_id=events)

stations = ebank.get_stations()
stations = stations.rename(columns={"calculated_latitude":"latitude",
                                    "calculated_longitude":"longitude",
                                    "confirmed_elevation":"elevation"
                                    }
                                    )
eqw = EQWindow(stations=stations,
               length=120,
                event_spacing="random",
                min_n_phase=-1,
                last_event_w=0.05
                )
eqw.add_events(cat.events)
eqw.add_noise(random_range=(200,500))

# print(eqw.timeline)
# print(eqw.arrivals.info())
# eqw.add_stations(stations_df=stations)


window_path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/window_test.png"
eqw.plot_window(save_path=window_path,
                show_moveout=True,
                show_phases="both",
                reference_location=None,
            show_station_labels=False)
# print(eqw)
exit()




# bank = EventBank(path)

# print(bank.get_stations().info())
# exit()

# savepath = "/groups/igonin/ecastillo/UTDQuake/test/10132025/test_bank.png" 
# bank.plot_overview(savepath=savepath)

# savepath = "/groups/igonin/ecastillo/UTDQuake/test/10132025/stats.png" 
# bank.plot_stats(savepath=savepath)

# savepath = "/groups/igonin/ecastillo/UTDQuake/test/10132025/station_location_uncertainty.png" 
# bank.plot_station_location_uncertainty(savepath=savepath)

# savepath = "/groups/igonin/ecastillo/UTDQuake/test/10132025/pick_histograms.png" 
# bank.plot_pick_histograms(savepath=savepath)

# savepath = "/groups/igonin/ecastillo/UTDQuake/test/10132025/uncertainty_boxplots.png" 
# bank.plot_uncertainty_boxplots(savepath=savepath)

# savepath = "/groups/igonin/ecastillo/UTDQuake/test/10132025/pick_stats.png" 
# bank.plot_pick_stats(savepath=savepath)

# print(bank.contributor)
# bank.save_picks()
# picks = bank.get_picks()
# print(picks.info())
# stations = bank.get_stations()
# station_details = bank.get_stations_details(stations=["PB24"])
# print(station_details)

# path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/tx/.stations/.TX_PB24.db"
# # table_names = fut.get_table_names(path)
# 
# x = fut._read_table(path , query)
# print(x)
# # print(table_names)