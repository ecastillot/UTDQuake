import os
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass

UTDQUAKE_ROOT: str = "UTDQUAKE_ROOT"
"""Environment variable name for UTDQuake cache root."""

HF_REPO_ID: str = "ecastillot/UTDQuake"
"""Hugging Face repository ID for UTDQuake dataset."""

HF_REPO_TYPE: str = "dataset"
"""Type of Hugging Face repository (default: 'dataset')."""

CORE_DIR: Path = Path(__file__).resolve().parent
"""Path to the core directory of the UTDQuake package."""

@dataclass(frozen=True)
class HFEntry:
    """
    Configuration entry for a Hugging Face dataset component.

    Attributes
    ----------
    name : str
        Dataset name or identifier (e.g., '0_networks').
    split : str
        Dataset split (e.g., 'metadata').
    path : str
        Relative path pattern for the dataset file.
    """
    name: Optional[str]
    split: Optional[str]
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
    Return the root directory for cached UTDQuake data.

    Users can override this location by setting the environment variable
    `UTDQUAKE_ROOT` before importing or using UTDQuake.

    If the variable is not set, the default location is:
    ``~/.utdquake``

    Returns
    -------
    Path
        Resolved path to the root cache directory.

    Examples
    --------
    >>> import os
    >>> os.environ["UTDQUAKE_ROOT"] = "/my/custom/cache"
    >>> from utdquake.core import get_root
    >>> root_path = get_root()
    >>> print(root_path)
    /my/custom/cache
    """
    root = os.environ.get(UTDQUAKE_ROOT, None)

    if root is None or str(root).strip() == "":
        # default Linux cache location
        root = os.path.join(Path.home(), ".utdquake")

    return Path(root).expanduser().resolve()