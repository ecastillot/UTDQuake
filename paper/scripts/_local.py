"""
Make the paper figures read UTDQuake 1.0 exactly as published: the Hugging Face tag ``v1.0`` at commit
:data:`REVISION`, in a local copy of its own (:data:`ROOT`). The working copy (UTDQuake_v2) keeps
growing (v2 events are added to v1 networks), so the paper does not read it. Import it before anything else:

    import _local  # noqa: F401

The copy is made once (``python _local.py``, see utdq_figures.sh): events, picks, stations, travel-time
models and stats of every v1 network, without the banks. DAS (UWF) is read the same way from the DAS
dataset at the same commit.
"""
import os
from pathlib import Path

#: Dataset version of the figures: PAPER_VERSION=v1 (default; UTDQuake 1.0 as published, a local copy of the Hub
#: tag) or v2 (the working copy UTDQuake_v2: v2.0 and the corrections listed under v2.1 in versions.rst).
#: Figures go to paper/<version>/.
VERSION = os.environ.get("PAPER_VERSION", "v1")
#: UTDQuake 1.0 on the Hub: tag v1.0 (moved 2026-11-02 for the JMA rename; see docs/source/versions.rst).
REVISION = "c5370c8d"
ROOTS = {"v1": "/groups/igonin/ecastillo/UTDQuake_paper_v1", "v2": "/groups/igonin/ecastillo/UTDQuake_v2"}
ROOT = ROOTS[VERSION]
#: Folder of the figures of this version.
OUT = Path(__file__).resolve().parents[1] / VERSION      # paper/<version>/ (scripts in paper/scripts/)
OUT.mkdir(exist_ok=True)
#: Figures made by the network figure pipeline (overview of UWF), from the working copy.
FIGURES = "/groups/igonin/ecastillo/UTDQuake_v2/figures"
os.environ["UTDQUAKE_ROOT"] = ROOT
os.environ["UTDQUAKE_DAS_ROOT"] = ROOT
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd  # noqa: E402

from utdquake.core.config import get_hf_entry, get_root  # noqa: E402
import utdquake.core.utdquake as utdquake_core  # noqa: E402
from utdquake.core.utdquake import Dataset  # noqa: E402


def networks(das: bool = False) -> pd.DataFrame:
    """Network table of the copy."""
    return pd.read_parquet(get_root(das) / get_hf_entry("networks", das).path)


def read(key: str, das: bool = False) -> pd.DataFrame:
    """Events or stations of every network of the copy, concatenated."""
    path = get_root(das) / get_hf_entry(key, das).path
    return pd.concat([pd.read_parquet(str(path).format(utdq_net=n)) for n in networks(das)["utdq_net"]],
                     ignore_index=True)


# read the copy's files directly (not the Hub, nor the datasets cache of another revision)
Dataset.networks = property(lambda self: networks(self.das))
Dataset.stations = property(lambda self: read("stations", self.das))
Dataset.events = property(lambda self: read("events", self.das))
# the copy has no banks: a network's tables are found without asking for its bank (Network.bank still does)
_resolve = utdquake_core.resolve_network_paths
utdquake_core.resolve_network_paths = lambda utdq_net, das=False, include_bank=False, **kw: _resolve(
    utdq_net, das=das, include_bank=include_bank, **kw)


def make_copy():
    """Download UTDQuake 1.0 (seismic and DAS) at :data:`REVISION` into :data:`ROOT`."""
    os.environ["HF_HUB_OFFLINE"] = "0"
    import huggingface_hub.constants as hub_constants
    hub_constants.HF_HUB_OFFLINE = False
    from huggingface_hub import snapshot_download

    from utdquake.core.data import download_snapshot
    for das in (False, True):
        download_snapshot(ROOT, utdq_nets="*", das=das, include_banks=False, include_travel_time=True,
                          overwrite=False, revision=REVISION)
    snapshot_download("ecastillot/UTDQuake", repo_type="dataset", revision=REVISION, local_dir=ROOT,
                      allow_patterns=[".utdquake/stats/*", ".utdquake_DAS/stats/*"])
    print(f"UTDQuake 1.0 ({REVISION}) in {ROOT}: {sorted(p.name for p in Path(ROOT).iterdir())}")


if __name__ == "__main__":
    make_copy()
