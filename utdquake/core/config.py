import os
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass, replace

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
        path="banks/{network}.zip",
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
    ".utdquake/travel_time": HFEntry(
        name=None,
        split=None,
        path=".utdquake/travel_time/{network}.parquet",
    ),
    ".utdquake/stats": HFEntry(
        name=None,
        split=None,
        path=".utdquake/stats/{network}.npz",
    ),
    ".utdquake/export": HFEntry(
        name=None,
        split=None,
        path=".utdquake/export",
    ),
    ".utdquake/logs": HFEntry(
        name=None,
        split=None,
        path=".utdquake/logs",
    ),
}

def get_hf_entry(key: str, das: bool = False) -> HFEntry:
    """
    Retrieve a Hugging Face dataset configuration entry.

    Parameters
    ----------
    key : str
        Configuration key defined in ``HF_CONFIG``.
    das : bool, default=False
        If ``True``, return the corresponding DAS-specific entry by
        modifying the dataset name and path as required.

    Returns
    -------
    HFEntry
        Configuration entry containing the dataset name, split, and
        relative file path.

    Notes
    -----
    For DAS datasets:

    - ``banks`` entries keep the same filename but are stored under a
      ``bank_DAS`` directory.
    - All other entries use a ``{key}_DAS`` directory and a dataset
      name suffixed with ``"_DAS"``.
    """
    entry = HF_CONFIG[key]

    if not das:
        return entry

    if key == "banks":
        # Replace "bank" with "bank_DAS" while preserving the filename.
        path = Path(entry.path)
        das_path = path.parent.with_name(f"{path.parent.name}_DAS") / path.name
        return replace(entry, path=str(das_path))

    elif ".utdquake" in key:
        path = Path(entry.path)
        first_part = path.parts[0]
        rest_parts = path.parts[1:]
        das_path = Path(f"{first_part}_DAS", *rest_parts)
        return replace(entry, path=str(das_path))
    
    # Store DAS files in a dedicated directory and append "_DAS"
    # to the dataset name when one exists.
    return replace(
        entry,
        name=f"{entry.name}_DAS" if entry.name else None,
        path=f"{key}_DAS/{Path(entry.path).name}",
    )

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

        - ``"banks"``: Path to the EventBank directory.
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
        "banks": root / get_hf_entry("banks",das).path.format(network=network).split(".zip")[0],
        "events": root / get_hf_entry("events",das).path.format(
            network=network
        ),
        "stations": root / get_hf_entry("stations",das).path.format(
            network=network
        ),
        "picks": root / get_hf_entry("picks",das).path.format(
            network=network
        ),

        ".utdquake/travel_time": root / get_hf_entry(".utdquake/travel_time",das).path.format(network=network),
        ".utdquake/stats": root / get_hf_entry(".utdquake/stats",das).path.format(network=network),

        # not for the public API
        ".utdquake/export/db": root / get_hf_entry(".utdquake/export",das).path / "db",
        ".utdquake/logs/banks": root / get_hf_entry(".utdquake/logs",das).path / f"{network}" / "banks",
    }


    # Ensure directories exist
    for path in utdq_paths.values():
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)

    return utdq_paths