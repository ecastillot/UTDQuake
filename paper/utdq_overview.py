import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import _local  # noqa: F401  (local UTDQuake 1.0 root, paper networks)

from pathlib import Path
import utdquake as utdq

# flagship figure of the README and docs (figures/utdquake_overview.png);
# station counts are distinct (network, station) pairs, see Dataset.description
fig_path = Path(__file__).parent.parent / "figures" / "utdquake_overview.png"
print(f"Saving figure to {fig_path}")

dataset = utdq.Dataset()
print(dataset.description)
dataset.plot_overview(savepath=fig_path, consider_calculated_stations=True, show=False)
