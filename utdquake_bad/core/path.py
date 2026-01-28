import os
from pathlib import Path
from .config import ENV_CACHE_ROOT,ENV_UTDQUAKE_MANUAL_INFO
from .config import CORE_DIR,DEFAULT_REPO_ID, DEFAULT_REPO_TYPE
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
    root = os.environ.get(ENV_CACHE_ROOT, None)

    if root is None or str(root).strip() == "":
        # default Linux cache location
        root = os.path.join(Path.home(), ".utdquake")

    return Path(root).expanduser().resolve()

def get_manual_info_path() -> Path:
    """
    Return the expected local path for the manual_info.csv file.
    """
    manual_info = os.environ.get(ENV_UTDQUAKE_MANUAL_INFO, None)

    if manual_info is None or str(manual_info).strip() == "":
        manual_info = CORE_DIR / "manual_info.csv"
    return Path(manual_info).expanduser().resolve()

def get_manifest_path() -> Path:
    """
    Return the expected local path for manifests.
    """
    return get_root() / "manifests"

def get_manifest_file_path(network: str, data_type: str) -> Path:
    """
    Return the expected local path for a network manifest file.
    """
    network = network.strip()
    data_type = data_type.strip()
    return get_manifest_path() / f"{data_type}" / f"network={network}.parquet"

def get_eventbank_path(network: str) -> Path:
    """
    Return the expected local path for a network EventBank.
    """
    network = network.strip()
    return get_root() / "events" / network