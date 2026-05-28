import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from pathlib import Path
import utdquake as utdq

fig_path = Path(__file__).parent / "utdq_density.png"
print(f"Saving figure to {fig_path}")

dataset = utdq.Dataset()
dataset.plot_network_station_density(savepath=fig_path)