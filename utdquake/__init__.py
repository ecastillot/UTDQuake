from .core.load import load_network
from .core.cache import list_local_networks
from huggingface_hub import HfApi

__version__ = "0.0.22"
__all__ = ["load_network"]

repo_id = "ecastillot/UTDQuake"
repo_type = "dataset"

# NETWORKS = []

# if list_local_networks():
#     for net in list_local_networks():
#         globals()[net] = lambda net=net, **kwargs: load_network(net, **kwargs)
#     __all__.extend(list_local_networks())


# __all__.extend(NETWORKS)


# api = HfApi()
# files = api.list_repo_files(repo_id , repo_type=repo_type)
# NETWORKS = sorted(f.split("/")[-1].replace(".zip", "") for f in files if f.endswith(".zip"))

# print(NETWORKS)

# # Create dynamic shortcut functions for each network
# for net in NETWORKS:
#     globals()[net] = lambda net=net, **kwargs: load_network(net, **kwargs)

# Add network shortcuts to __all__
# __all__.extend(NETWORKS)