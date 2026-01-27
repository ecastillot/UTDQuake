from utdquake.bank.bank import EventBank
import obsplus
import obspy
from utdquake.utils.plot import EQWindow
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.gridspec as gridspec
import numpy as np

path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/tx"
ebank = EventBank(path)
metadata = ebank.read_index()

fig = plt.figure(figsize=(16, 8))

# Define positions manually: [left, bottom, width, height] in figure fraction
# 5 columns: first 3 normal, 1 spacer, last column
gs = gridspec.GridSpec(3, 5, figure=fig, 

                    width_ratios=[1,1,1,0.1,1], wspace=0.3)

axes = [[None for _ in range(4)] for _ in range(3)]  # 3 rows x 4 columns

for i in range(3):
    # First 3 columns
    for j in range(3):
        ax = fig.add_subplot(gs[i, j])
        # ax.set_title(f"Row {i+1}, Col {j+1}")
        axes[i][j] = ax  # store reference

    # 4th column (last column)
    ax = fig.add_subplot(gs[i, 4])
    # ax.set_title(f"Row {i+1}, Col 4")
    axes[i][3] = ax  # store reference (index 3 = 4th column)


# events = metadata.iloc[30:35]
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

        ax = axes[i][j]

        print(cat)

        # exit()
        stations = ebank.get_stations()
        stations = stations.rename(columns={"calculated_latitude":"latitude",
                                            "calculated_longitude":"longitude",
                                            "confirmed_elevation":"elevation"
                                            }
                                        )
        eqw = EQWindow(stations=stations,
                    length=120,
                        event_spacing="random",
                        min_n_phase=4,
                        last_event_w=0.05
                        )
        eqw.add_events(cat.events)
        eqw.add_noise(random_range=noise)


        _ax = eqw.plot_window(
                        show_moveout=True,
                        show_phases="both",
                        reference_location=None,
                    show_station_labels=False,
                    show_earthquake_lines=False,
                    show_legend=False,
                    show=False,
                    ax = ax
                    )
        
        if i!=0:
            # remove x label
            _ax.set_xlabel("")
        if j!=0:
            # remove y label
            _ax.set_ylabel("")

        plt.savefig("/groups/igonin/ecastillo/UTDQuake/test/10132025/window_test_all.png")
    # print(eqw)


windows = [50,100,200]

for i,w in enumerate(windows):
    # print(noise,events)

    events = metadata.sample(n=5, replace=False)

    cat = ebank.get_events(event_id=events["event_id"].tolist())

    ax = axes[i][3]

    print(cat)

    # exit()
    stations = ebank.get_stations()
    stations = stations.rename(columns={"calculated_latitude":"latitude",
                                        "calculated_longitude":"longitude",
                                        "confirmed_elevation":"elevation"
                                        }
                                    )
    eqw = EQWindow(stations=stations,
                length=w,
                    event_spacing="random",
                    min_n_phase=4,
                    last_event_w=0.05
                    )
    eqw.add_events(cat.events)
    eqw.add_noise(random_range=noise)


    _ax = eqw.plot_window(
                    show_moveout=True,
                    show_phases="both",
                    reference_location=None,
                show_station_labels=False,
                show_earthquake_lines=False,
                show_legend=False,
                show=False,
                ax = ax
                )
    
    if i!=0:
        # remove x label
        _ax.set_xlabel("")


plt.tight_layout()  # now works because axes are compatible
plt.savefig("/groups/igonin/ecastillo/UTDQuake/test/10132025/window_test_all.png")

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