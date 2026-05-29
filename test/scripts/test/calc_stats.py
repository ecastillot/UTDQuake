import os 

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from pathlib import Path
import utdquake as utdq


# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

dataset = utdq.Dataset()
print(dataset)

dataset.compute_stats(networks=["RSNC"], merge=True)

print(dataset.stats)
path = Path(__file__).parent / "stats.png"
dataset.plot_stats(savepath=path)

# print(stats)
# # network level
# network_data = dataset.networks
# network_names = network_data["network"].tolist()

# network = dataset.get_network(name=network_names[0])
# network.compute_stats()
# print(network)
