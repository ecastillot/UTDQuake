import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import _local  # noqa: F401  (local UTDQuake 1.0 root, paper networks)

from pathlib import Path
import utdquake as utdq

fig_path = _local.OUT / "utdq_density.png"
print(f"Saving figure to {fig_path}")

dataset = utdq.Dataset()
# v2: ~4x more events per network than v1 -> smaller markers, network codes centred on them
opts = {"v1": {}, "v2": {"size_per_event": 0.025, "center_labels": True}}[_local.VERSION]
dataset.plot_network_station_density(savepath=fig_path, **opts)