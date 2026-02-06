from __future__ import annotations
from huggingface_hub import HfApi
import os
from pathlib import Path
import pandas as pd
import concurrent.futures as cf
from .config import ENV_CACHE_ROOT, DEFAULT_REPO_ID, DEFAULT_REPO_TYPE
from ..bank.bank import EventBank
from .path import get_root, get_eventbank_path


def network_exists_locally(network: str) -> bool:
    path = get_eventbank_path(network)
    return path.exists() and any(path.iterdir())

def list_remote_networks(repo_id: str = DEFAULT_REPO_ID) -> list[str]:
    """Return all networks available in the HF repo (without downloading)."""
    api = HfApi()
    files = api.list_repo_files(repo_id, repo_type=DEFAULT_REPO_TYPE)
    return sorted(f.split("/")[-1].replace(".zip", "") for f in files if f.endswith(".zip"))

def list_local_networks() -> list[str]:
    """Return all networks available locally."""
    root = get_root() / "bank"
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir() and any(p.iterdir())])

def list_all_networks(repo_id: str = DEFAULT_REPO_ID) -> list[str]:
    # Check local first
    root = get_root() / "bank"
    local_networks = sorted([p.name for p in root.iterdir() if p.is_dir() and any(p.iterdir())])
    if local_networks:
        return local_networks

    # Otherwise, fetch from HF
    api = HfApi()
    files = api.list_repo_files(repo_id, repo_type=DEFAULT_REPO_TYPE)
    networks = sorted(f.split("/")[-1].replace(".zip", "") for f in files if f.endswith(".zip"))
    return networks


def _append_fdsn_info(stats: pd.DataFrame) -> pd.DataFrame:
    """
    Append FDSN metadata (url, notes) to a stats DataFrame.

    Parameters
    ----------
    stats : pandas.DataFrame
        Input DataFrame containing at least a "contributor" column.

    Returns
    -------
    pandas.DataFrame
        Merged DataFrame with FDSN information appended and columns reordered.
    """
    fdsn_df = pd.read_csv(FDSN_CSV)

    merged = pd.merge(
        fdsn_df,
        stats,
        on="contributor",
        how="right",
    )

    # Move "url" and "notes" to the last columns (if they exist).
    cols = merged.columns.tolist()
    for col in ["url", "notes"]:
        if col in cols:
            cols.remove(col)
            cols.append(col)

    return merged[cols]

def create_report(save_path: str | None = None, max_workers: int | None = None):
    """
    Load all events and stations from local networks in parallel,
    append FDSN info to stats, and optionally save them as CSV files.

    Parameters
    ----------
    save_path : str | None
        Directory where CSV files will be saved. If None, data is not saved.
    max_workers : int | None
        Number of threads to use for parallel loading.

    Returns
    -------
    all_stats : pd.DataFrame
        Concatenated DataFrame of network stats.
    all_events : pd.DataFrame
        Concatenated DataFrame of events from all local networks.
    all_stations : pd.DataFrame
        Concatenated DataFrame of stations from all local networks.
    """
    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)
        stats_file = os.path.join(save_path, "stats.csv")
        events_file = os.path.join(save_path, "events.csv")
        stations_file = os.path.join(save_path, "stations.csv")

        # If files already exist, just load them
        if os.path.exists(stats_file) and os.path.exists(events_file) and os.path.exists(stations_file):
            all_stats = pd.read_csv(stats_file)
            all_events = pd.read_csv(events_file)
            all_stations = pd.read_csv(stations_file)
            return all_stats, all_events, all_stations

    def _load_one_network(net: str):
        path = get_eventbank_path(net)
        bank = EventBank(str(path))
        stats = pd.DataFrame([bank.stats])
        stats = _append_fdsn_info(stats)
        return stats, bank.read_index(), bank.get_stations()

    networks = list_local_networks()

    if not networks:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if max_workers is None:
        max_workers = min(32, (os.cpu_count() or 1) + 4)
    if len(networks) < max_workers:
        max_workers = len(networks)

    all_stats, all_events, all_stations = [], [], []

    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for stats, events, stations in executor.map(_load_one_network, networks):
            all_stats.append(stats)
            all_events.append(events)
            all_stations.append(stations)

    all_stats = pd.concat(all_stats, ignore_index=True)
    all_events = pd.concat(all_events, ignore_index=True)
    all_stations = pd.concat(all_stations, ignore_index=True)

    # Save if save_path is provided
    if save_path is not None:
        all_stats.to_csv(stats_file, index=False)
        all_events.to_csv(events_file, index=False)
        all_stations.to_csv(stations_file, index=False)

    return all_stats, all_events, all_stations



if __name__ == "__main__":
    test = get_eventbank_path("tx")
    print(test)