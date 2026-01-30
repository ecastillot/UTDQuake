import os
from typing import Dict
from pathlib import Path
from dataclasses import dataclass

UTDQUAKE_ROOT = "UTDQUAKE_ROOT"
HF_REPO_ID = "ecastillot/UTDQuake"
HF_REPO_TYPE = "dataset"

CORE_DIR = Path(__file__).resolve().parent

@dataclass(frozen=True)
class HFEntry:
    """
    Configuration entry for a Hugging Face dataset component.
    """
    name: str
    split: str
    path: str

HF_CONFIG: Dict[str, HFEntry] = {
    "banks": HFEntry(
        name=None,
        split=None,
        path="bank/{network}.zip",
    ),
    "networks": HFEntry(
        name="0_networks",
        split="metadata",
        path="network/network.parquet",
    ),
    "stations": HFEntry(
        name="1_stations",
        split="metadata",
        path="stations/network={network}.parquet",
    ),
    "events": HFEntry(
        name="2_events",
        split="metadata",
        path="events/network={network}.parquet",
    ),
    "picks": HFEntry(
        name="3_picks",
        split="metadata",
        path="picks/network={network}.parquet",
    ),
}


def get_root() -> Path:
    """
    Return the root directory used to store cached UTDQuake data.

    Users can override this location by setting the environment variable
    `UTDQUAKE_ROOT` before importing/using utdquake:

    Example
    -------
    >>> import os
    >>> os.environ["UTDQUAKE_ROOT"] = "/my/custom/cache"
    """
    root = os.environ.get(UTDQUAKE_ROOT, None)

    if root is None or str(root).strip() == "":
        # default Linux cache location
        root = os.path.join(Path.home(), ".utdquake")

    return Path(root).expanduser().resolve()