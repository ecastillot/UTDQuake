import os
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass

UTDQUAKE_ROOT: str = "UTDQUAKE_ROOT"
"""Environment variable name for UTDQuake cache root."""

UTDQUAKE_DAS_ROOT: str = "UTDQUAKE_DAS_ROOT"
"""Environment variable name for UTDQuake DAS cache root."""

HF_REPO_ID: str = "ecastillot/UTDQuake"
"""Hugging Face repository ID for UTDQuake dataset."""

HF_REPO_TYPE: str = "dataset"
"""Type of Hugging Face repository (default: 'dataset')."""

CORE_DIR: Path = Path(__file__).resolve().parent
"""Path to the core directory of the UTDQuake package."""

KM_PER_DEG = 111.19

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

def get_hf_entry(key: str, das: bool = False) -> HFEntry:
    """
    Return a Hugging Face configuration entry.

    Parameters
    ----------
    key : str
        Configuration key.
    das : bool, optional
        If True, use DAS dataset names.

    Returns
    -------
    HFEntry
    """

    entry = HF_CONFIG[key]

    if das and entry.name is not None:
        return HFEntry(
            name=f"{entry.name}_DAS",
            split=entry.split,
            path=entry.path,
        )

    return entry

def get_root(das: bool = False) -> Path:
    """
    Return the root directory for cached UTDQuake data.

    Users can override this location by setting the environment variable
    `UTDQUAKE_ROOT` or `UTDQUAKE_DAS_ROOT` before importing or using
    UTDQuake.

    If the variable is not set, the default locations are:

    - ``~/.utdquake``
    - ``~/.utdquake_das`` (for DAS data)`

    Parameters
    ----------
    das : bool, optional
        If True, use the DAS cache root environment variable
        (`UTDQUAKE_DAS_ROOT`). Otherwise use the standard cache root
        (`UTDQUAKE_ROOT`).

    Returns
    -------
    Path
        Resolved path to the root cache directory.

    Examples
    --------
    >>> import os
    >>> os.environ["UTDQUAKE_ROOT"] = "/my/custom/cache"
    >>> root_path = get_root()
    >>> print(root_path)
    /my/custom/cache

    >>> os.environ["UTDQUAKE_DAS_ROOT"] = "/my/das/cache"
    >>> das_root = get_root(das=True)
    >>> print(das_root)
    /my/das/cache
    """

    env_var = UTDQUAKE_DAS_ROOT if das else UTDQUAKE_ROOT

    root = os.environ.get(env_var, None)

    if root is None or str(root).strip() == "":
        # default Linux cache location
        if das:
            root = os.path.join(Path.home(), ".utdquake_das")
        else:
            root = os.path.join(Path.home(), ".utdquake")

    return Path(root).expanduser().resolve()

def get_utdq_paths(network: str, das: bool = False) -> Dict[str, Path]:
    """
    Return standardized UTDQuake directory paths for a given network.

    This helper constructs the filesystem paths used by UTDQuake
    for storing and accessing data products associated with a
    seismic network.

    Parameters
    ----------
    network : str
        Network code (e.g., ``"tx"``, ``"AK"``, etc.).
    das : bool, optional
        If True, use the DAS cache root environment variable
        (`UTDQUAKE_DAS_ROOT`). Otherwise use the standard cache root
        (`UTDQUAKE_ROOT`).

    Returns
    -------
    dict of str to pathlib.Path
        Dictionary containing the following keys:

        - ``"bank"``: Path to the EventBank directory.
        - ``"events"``: Path to event files.
        - ``"stations"``: Path to station metadata.
        - ``"picks"``: Path to pick files.

    Notes
    -----
    - Paths are constructed relative to the root directory
      returned by :func:`get_root`.
    - Subdirectory templates are defined in :data:`HF_CONFIG`.
    """

    root = get_root(das=das)

    utdq_paths = {
        "banks": root / "bank" / network,
        "events": root / get_hf_entry("events",das).path.format(
            network=network
        ),
        "stations": root / get_hf_entry("stations",das).path.format(
            network=network
        ),
        "picks": root / get_hf_entry("picks",das).path.format(
            network=network
        ),


        "utdq/models/picks": root / ".utdquake" / "models" / "picks"/  f"{network}.parquet",
        "utdq/stats": root / ".utdquake" / "stats" / f"{network}.npz",

        "utdq/db/events": root / ".utdquake" / "db" / "events" / f"{network}.db",
        "utdq/db/stations": root / ".utdquake"  / "db" / "stations" / f"{network}.db",
        "utdq/db/.stations": root / ".utdquake"  / "db" / "stations" / f".{network}",
        "utdq/db/picks": root / ".utdquake"  / "db" / "picks" / f"{network}.db",
    }

    # Ensure directories exist
    for key, path in utdq_paths.items():
        if key == "banks" or key=="utdq/db/.stations":
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)

    return utdq_paths