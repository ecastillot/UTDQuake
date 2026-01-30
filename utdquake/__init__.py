"""
UTDQuake Python Package
=======================

Provides convenient access to the UTDQuake seismic dataset. The package
includes:

- `Dataset`: Class for global dataset access (all networks, stations, events).
- `Network`: Class for network-specific access, including EventBank, picks, and stations.
- `download_snapshot`: Function to download UTDQuake data from Hugging Face.
- `load`: Function to load datasets from Hugging Face by key.

Usage
-----

>>> from utdquake import Dataset
>>> ds = Dataset()
>>> ds.stations.head()
>>> net = ds.get_network("tx")
>>> net.events.head()

"""
__version__ = "0.1"

from .core.utdquake import Dataset, Network
from .core.data import download_snapshot, load

__all__ = ["Dataset", "Network", "download_snapshot", "load"]