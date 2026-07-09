import os 
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
os.environ["UTDQUAKE_DAS_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

from pathlib import Path
from obsplus import EventBank
import utdquake as utdq
import concurrent.futures as cf



dataset = utdq.Dataset(das=True) # set das=True to load DAS data
print(dataset.networks)
network = dataset.get_network(name="UWF")
print(network)
print(network.events)