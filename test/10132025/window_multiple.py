from utdquake.bank.bank import EventBank
import obsplus
import obspy
from utdquake.utils.plot import EQWindow
import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np

path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/tx"
ebank = EventBank(path)
metadata = ebank.read_index()

folder = "/groups/igonin/ecastillo/UTDQuake/test/10132025/window_multiple/"
os.makedirs(folder, exist_ok=True)


x1 = 1,5
x2 = 5,10
x3 = 10,15
n_events = [x1, x2, x3]

r_0 = (0,100)
r_1 = (100,200)
r_2 = (300,500)
n_noise = [r_0, r_1, r_2]

for i,noise in enumerate(n_noise ):
    for j,n_ev in enumerate(n_events):
        # print(noise,events)
        x1, x2 = n_ev
        n = np.random.randint(x1, x2 + 1)
        events = metadata.sample(n=n, replace=False)

        cat = ebank.get_events(event_id=events["event_id"].tolist())


        # cat = ebank.get_events(event_id=events)

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


        window_path = os.path.join(folder,f"window_{i}_{j}.png")
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