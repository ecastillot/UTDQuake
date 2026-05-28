import os 
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
os.environ["UTDQUAKE_DAS_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

from pathlib import Path
import utdquake as utdq

from utdquake.core.config import get_utdq_paths, get_hf_entry


# figs_path = Path(__file__).parent.parent.parent / "figures"
figs_path = Path(__file__).parent / "figures"
figs_path.mkdir(exist_ok=True)
print(f"Saving figure to {figs_path}")

dataset = utdq.Dataset(das=True)
print(dataset)
network = dataset.get_network("GCI")
events = network.events

path= "/groups/igonin/ecastillo/utdquake/scripts2/das_fig/ak_network/0.das_events.csv"
events.to_csv(path,index=False)