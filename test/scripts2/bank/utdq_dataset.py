import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
os.environ["UTDQUAKE_ROOT_DAS"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

from pathlib import Path
import utdquake as utdq

# fig_path = Path(__file__).parent / "utdq_density.png"
# print(f"Saving figure to {fig_path}")

dataset = utdq.Dataset(das=True)
network_data = dataset.networks
print(network_data)
network = dataset.get_network(name="GCI")
print(network)


# # events
# events = network.events
# print(events)

# # stations
# stations = network.stations
# print(stations)

# # picks
# picks = network.picks
# print(picks)

# dataset.plot_network_station_density(savepath=fig_path)