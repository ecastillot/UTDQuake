from __future__ import annotations
from huggingface_hub import HfApi
import os
from pathlib import Path


ENV_CACHE_ROOT = "UTDQUAKE_ROOT"


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


def get_eventbank_path(network: str) -> Path:
    """
    Return the expected local path for a network EventBank.
    """
    network = network.strip()
    return get_root() / "events" / network

def network_exists_locally(network: str) -> bool:
    path = get_eventbank_path(network)
    return path.exists() and any(path.iterdir())

def list_remote_networks(repo_id="ecastillot/UTDQuake") -> list[str]:
    """Return all networks available in the HF repo (without downloading)."""
    api = HfApi()
    files = api.list_repo_files(repo_id, repo_type="dataset")
    return sorted(f.split("/")[-1].replace(".zip", "") for f in files if f.endswith(".zip"))

def list_local_networks() -> list[str]:
    """Return all networks available locally."""
    root = get_root() / "events"
    local_networks = sorted([p.name for p in root.iterdir() if p.is_dir() and any(p.iterdir())])
    if local_networks:
        return local_networks

def list_all_networks(repo_id="ecastillot/UTDQuake") -> list[str]:
    # Check local first
    root = get_root() / "events"
    local_networks = sorted([p.name for p in root.iterdir() if p.is_dir() and any(p.iterdir())])
    if local_networks:
        return local_networks

    # Otherwise, fetch from HF
    api = HfApi()
    files = api.list_repo_files(repo_id, repo_type="dataset")
    networks = sorted(f.split("/")[-1].replace(".zip", "") for f in files if f.endswith(".zip"))
    return networks



if __name__ == "__main__":
    test = get_eventbank_path("tx")
    print(test)