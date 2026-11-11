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

UTDQUAKE_REVISION: str = "UTDQUAKE_REVISION"
"""Environment variable name for the Hugging Face revision to read (a branch,
tag such as ``v1.0``, commit hash or ``refs/pr/N``). Unset: ``main``."""

CORE_DIR: Path = Path(__file__).resolve().parent
"""Path to the core directory of the UTDQuake package."""

KM_PER_DEG = 111.19

UTDQ_NET: str = "utdq_net"
"""Column (and file key) that names a UTDQuake network: the key of the
network table and of every events/stations/picks file. A UTDQuake network
is the monitoring network or project that reported the events and picks
(e.g. ``tx``, ``AEIC``, ``R05``). The ``network`` column of the stations and
picks tables is something else: the FDSN code of the recording station."""

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
        path="banks/{utdq_net}.zip",
    ),
    "networks": HFEntry(
        name="0_networks",
        split="metadata",
        path="network/network.parquet",
    ),
    "stations": HFEntry(
        name="1_stations",
        split="metadata",
        path="stations/utdq_net={utdq_net}.parquet",
    ),
    "events": HFEntry(
        name="2_events",
        split="metadata",
        path="events/utdq_net={utdq_net}.parquet",
    ),
    "picks": HFEntry(
        name="3_picks",
        split="metadata",
        path="picks/utdq_net={utdq_net}.parquet",
    ),
    ".utdquake/travel_time": HFEntry(
        name=None,
        split=None,
        path=".utdquake/travel_time/{utdq_net}.parquet",
    ),
    ".utdquake/stats": HFEntry(
        name=None,
        split=None,
        path=".utdquake/stats/{utdq_net}.npz",
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
    
    # Store DAS files in a dedicated directory (the entry's own directory
    # with "_DAS", e.g. network/ -> network_DAS/) and append "_DAS" to the
    # dataset name when one exists.
    path = Path(entry.path)
    return replace(
        entry,
        name=f"{entry.name}_DAS" if entry.name else None,
        path=f"{path.parent.name}_DAS/{path.name}",
    )

def get_revision(revision: Optional[str] = None) -> Optional[str]:
    """
    Return the Hugging Face revision to read: ``revision`` if given, else the
    ``UTDQUAKE_REVISION`` environment variable, else None (``main``).

    Examples
    --------
    >>> os.environ["UTDQUAKE_REVISION"] = "v1.0"
    >>> get_revision()
    'v1.0'
    """
    if revision is None:
        revision = os.environ.get(UTDQUAKE_REVISION, "").strip() or None
    return revision


def released_versions(repo_id: str = None) -> list:
    """Released dataset versions: the ``vMAJOR.MINOR`` tags of the Hub repository, oldest first (needs the
    network; [] if it cannot be reached)."""
    import re
    try:
        from huggingface_hub import HfApi
        refs = HfApi().list_repo_refs(repo_id or HF_REPO_ID, repo_type=HF_REPO_TYPE)
    except Exception:
        return []
    tags = [t.name for t in refs.tags if re.fullmatch(r"v\d+\.\d+", t.name)]
    return sorted(tags, key=lambda t: tuple(int(x) for x in t[1:].split(".")))


def next_dataset_version(repo_id: str = None) -> Optional[str]:
    """The release new data goes into: the latest released version plus one minor version (``v2.0`` ->
    ``v2.1``). New networks and events are labelled with it (``dataset_version``). None if the Hub cannot
    be reached."""
    released = released_versions(repo_id)
    if not released:
        return None
    major, minor = (int(x) for x in released[-1][1:].split("."))
    return f"v{major}.{minor + 1}"


def set_version(version: Optional[str]) -> None:
    """Read dataset ``version`` (tag, ``main`` or commit) from now on: sets ``UTDQUAKE_REVISION``."""
    if version is None or str(version).strip() in ("", "main"):
        os.environ.pop(UTDQUAKE_REVISION, None)
    else:
        os.environ[UTDQUAKE_REVISION] = str(version).strip()


def get_root(das: bool = False) -> Path:
    """
    Return the root directory for cached UTDQuake data.

    Users can override this location by setting the environment variable
    `UTDQUAKE_ROOT` or `UTDQUAKE_DAS_ROOT` before importing or using
    UTDQuake.

    If the variable is not set, the default locations are one folder per dataset version (the
    ``UTDQUAKE_REVISION`` / ``Dataset(version=...)``, ``main`` if none):

    - ``~/.utdquake/<version>`` (e.g. ``~/.utdquake/v2.0``)
    - ``~/.utdquake_das/<version>`` (for DAS data)

    A root set with the variable is used as is, whatever the version.

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

    if root is not None and str(root).strip() != "":
        # a root you chose is used as is (one dataset version per folder: you choose the folder)
        return Path(root).expanduser().resolve()
    # default cache: one folder per dataset version (~/.utdquake/v2.0, ~/.utdquake/main), so that files of
    # different versions are never mixed and a newer version is never read from an older download
    base = os.path.join(Path.home(), ".utdquake_das" if das else ".utdquake")
    return (Path(base) / version_folder(get_revision())).expanduser().resolve()


def version_folder(revision: Optional[str]) -> str:
    """Folder name of a dataset version in the default cache: the tag (``v2.0``), ``main`` when none is set,
    or the revision with ``/`` replaced (``refs_pr_3``)."""
    return (revision or "main").replace("/", "_")


#: File in a local root recording the version its files were downloaded from.
SNAPSHOT_FILE = ".utdquake/snapshot.json"


def read_snapshot(root: Path) -> Optional[dict]:
    """The version a local root was downloaded from (``revision``, Hub ``commit``, ``date``), or None."""
    import json
    path = Path(root) / SNAPSHOT_FILE
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def write_snapshot(root: Path, revision: Optional[str], commit: Optional[str]) -> None:
    """Record in ``root`` the version and Hub commit its files were downloaded from."""
    import datetime
    import json
    path = Path(root) / SNAPSHOT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"revision": revision or "main", "commit": commit,
                                "date": datetime.datetime.now().isoformat(timespec="seconds")}, indent=1))

def get_utdq_paths(utdq_net: str, das: bool = False) -> Dict[str, Path]:
    """
    Return standardized UTDQuake directory paths for a given UTDQuake network.

    This helper constructs the filesystem paths used by UTDQuake
    for storing and accessing data products associated with a
    UTDQuake network (``utdq_net``).

    Parameters
    ----------
    utdq_net : str
        UTDQuake network code (e.g., ``"tx"``, ``"AEIC"``, ``"R05"``), the
        key of the network table. Not an FDSN network code: those are the
        ``network`` column of the stations and picks tables.
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

    def fmt(key):
        return get_hf_entry(key, das).path.format(utdq_net=utdq_net)

    utdq_paths = {
        "banks": root / fmt("banks").split(".zip")[0],
        "events": root / fmt("events"),
        "stations": root / fmt("stations"),
        "picks": root / fmt("picks"),

        ".utdquake/travel_time": root / fmt(".utdquake/travel_time"),
        ".utdquake/stats": root / fmt(".utdquake/stats"),

        # not for the public API
        ".utdquake/export/db": root / get_hf_entry(".utdquake/export",das).path / "db",
        ".utdquake/logs/banks": root / get_hf_entry(".utdquake/logs",das).path / f"{utdq_net}" / "banks",
    }


    # Ensure directories exist
    for path in utdq_paths.values():
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)

    return utdq_paths
