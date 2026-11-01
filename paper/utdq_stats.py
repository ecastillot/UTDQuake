import os
import _local  # noqa: F401  (local UTDQuake 1.0 root, paper networks)

from pathlib import Path
import utdquake as utdq

fig_path = Path(__file__).parent / "utdq_stats.png"
print(f"Saving figure to {fig_path}")

dataset = utdq.Dataset()
network_data = dataset.networks
network_names = network_data["utdq_net"].tolist()

# network_names = ["RSNC"]

dataset = utdq.Dataset()
dataset.compute_stats(networks=network_names, merge=True)

dataset.plot_stats(savepath=fig_path)


