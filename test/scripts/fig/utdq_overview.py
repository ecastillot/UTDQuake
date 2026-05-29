import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from pathlib import Path
import utdquake as utdq


figs_path = Path(__file__).parent.parent.parent / "figures"
print(f"Saving figure to {figs_path}")


# utdq_fig = utdq.Dataset().plot_overview(savepath=figs_path / "utdquake.png")
dataset = utdq.Dataset()
# dataset.plot_overview(savepath=figs_path / "utdquake_overview.png",
#                     consider_calculated_stations= True)
dataset.plot_travel_time_vs_distance(savepath=figs_path / "t.png")
# dataset.plot_network_station_density(savepath=figs_path / "utdquake_network_station_density.png")
# dataset.plot_phase_count_radar_by_magnitude(savepath=figs_path / "utdquake_phase_count_radar_by_magnitude.png")

# if stations_type in ["calculated"]:
#     #qc 
#     stations = stations.drop_duplicates(subset=["network", 
#                                                 "station"])
#     stations = stations[stations["num_entries"]>10]
#     stations = stations[stations["calculated_latitude_iqr"]<0.1]
#     stations = stations[stations["calculated_longitude_iqr"]<0.1]