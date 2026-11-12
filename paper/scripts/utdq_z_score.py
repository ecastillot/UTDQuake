import os
import _local  # noqa: F401  (local UTDQuake 1.0 root, paper networks)

from pathlib import Path
import utdquake as utdq
from utdquake.utils.plot import plot_travel_time_vs_distance_zscore

fig_path = _local.OUT / "utdq_z_score.png"
print(f"Saving figure to {fig_path}")

dataset = utdq.Dataset()
network = dataset.get_network("tx")
picks = network.picks

plot_travel_time_vs_distance_zscore(picks,
                                    phase="P",
                                    distance_unit="hypo_km",
                                    x_lim=(0,300),
                                    y_lim=(0,50),
                                    savepath=fig_path)  

print(picks)


