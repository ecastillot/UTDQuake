"""
UTDQuake Python Package
=======================

Provides convenient access to the UTDQuake seismic dataset. The package
includes:

- `Dataset`: Class for global dataset access (all networks, stations, events).
- `Network`: Class for network-specific access, including EventBank, picks, and stations.
- `download_snapshot`: Function to download UTDQuake data from Hugging Face.
- `load`: Function to load datasets from Hugging Face by key.
- `publish_network`: Function to publish a network's manifests to the shared Hub repo.
- `remove_network`: Function to remove a network's files from the shared Hub repo.
- `generate_network_figures`: Function to generate a network's documentation figures.
- `publish_network_figures`: Function to publish those figures to GitHub.

Usage
-----

>>> from utdquake import Dataset
>>> ds = Dataset()
>>> ds.stations.head()
>>> net = ds.get_network("tx")
>>> net.events.head()

"""
__version__ = "0.2.3"

from .core.utdquake import Dataset, Network
from .core.data import download_snapshot, load
from .core.patch import utdquake_obspy_patch
from .hub import publish_network, remove_network
from .figures import generate_network_figures, publish_network_figures

utdquake_obspy_patch()
__all__ = [
    "Dataset", "Network", "download_snapshot", "load",
    "publish_network", "remove_network",
    "generate_network_figures", "publish_network_figures",
]
