"""
Make the paper figures read the local UTDQuake 1.0 root (UTDQuake_v2),
restricted to the networks of the paper (``dataset_version == "v1"``), until
v1.0 is published on the Hugging Face Hub. Import it before anything else:

    import _local  # noqa: F401

Once v1.0 is on the Hub, the scripts can read it instead with
``UTDQUAKE_REVISION=v1.0`` and this module can go.
"""
import os

ROOT = "/groups/igonin/ecastillo/UTDQuake_v2"
VERSION = "v1"
os.environ["UTDQUAKE_ROOT"] = ROOT
os.environ["UTDQUAKE_DAS_ROOT"] = ROOT
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd  # noqa: E402

from utdquake.core.config import get_hf_entry, get_root  # noqa: E402
from utdquake.core.utdquake import Dataset  # noqa: E402


def networks(das: bool = False) -> pd.DataFrame:
    """Local network table, paper networks only."""
    table = pd.read_parquet(get_root(das) / get_hf_entry("networks", das).path)
    return table[table["dataset_version"] == VERSION].reset_index(drop=True)


def read(key: str, das: bool = False) -> pd.DataFrame:
    """Local events or stations of the paper networks, concatenated."""
    path = get_root(das) / get_hf_entry(key, das).path
    return pd.concat([pd.read_parquet(str(path).format(utdq_net=n)) for n in networks(das)["utdq_net"]],
                     ignore_index=True)


Dataset.networks = property(lambda self: networks(self.das))
Dataset.stations = property(lambda self: read("stations", self.das))
Dataset.events = property(lambda self: read("events", self.das))
