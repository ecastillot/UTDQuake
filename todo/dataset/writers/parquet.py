from __future__ import annotations

import os
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Dict, List

import pandas as pd

from ...core.config import HF_CONFIG,get_root,get_utdq_paths
from ...utils.cache import list_local_networks
from ..manager.manager import UTDQBank
from .manifest import ManifestPaths, ManifestProgress
from .schema import (PREF_PICKS_ORDER,
                    PREF_PICKS_TYPES,
                    PREF_EVENTS_ORDER,
                    PREF_EVENTS_TYPES,
                    PREF_NETWORK_ORDER,
                    PREF_NETWORK_TYPES,
                    PREF_STATIONS_ORDER,
                    PREF_STATIONS_TYPES,
                    sanitize_dataframe_for_parquet)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _safe_concat(existing: Optional[pd.DataFrame], new: pd.DataFrame) -> pd.DataFrame:
    if existing is None or existing.empty:
        return new
    return pd.concat([existing, new], ignore_index=True)

def _write_parquet_atomic(df: pd.DataFrame, out_path: Path) -> None:
    """
    Write parquet atomically to avoid corruption if interrupted mid-write.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    df.to_parquet(tmp_path, index=False)
    tmp_path.replace(out_path)


def _append_parquet_dedup(
    out_path: Path,
    new_df: pd.DataFrame,
    subset_cols: List[str],
) -> None:
    """
    Append-like behavior for parquet:
    - read existing parquet if present
    - concat + drop duplicates
    - write atomically

    This is safe but can become heavy when the parquet grows huge.
    For very large datasets, you should switch to per-network parquet shards.
    """
    out_path = Path(out_path)

    if out_path.exists():
        old = pd.read_parquet(out_path)
        combined = pd.concat([old, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=subset_cols, keep="last")
    else:
        combined = new_df.drop_duplicates(subset=subset_cols, keep="last")

    _write_parquet_atomic(combined, out_path)


def build_manifests(
    networks: Optional[Iterable[str]] = None,
    force_download: bool = False,
    overwrite: bool = False,
    include_events: bool = True,
    include_stations: bool = True,
    include_picks: bool = True,
    include_networks: bool = True,
    include_manual_network_info: pd.DataFrame = None
) -> ManifestPaths:
    """
    Build UTDQuake manifest files incrementally, resume-safe.

    Key ideas:
    - process one network at a time
    - save output after each network
    - track progress in SQLite so you can resume safely
    - saves one parquet per network per manifest type, e.g.
        manifests/events/network=tx.parquet
        manifests/picks/network=tx.parquet

    Parameters
    ----------
    networks
        Networks to process. If None, uses local networks.
    force_download
        If True, download missing networks.
    overwrite
        If True, delete progress and rebuild from scratch.
    include_events, include_stations, include_picks, include_networks
        Which manifests to build.

    Returns
    -------
    ManifestPaths
    """

    root = get_root()
    paths = ManifestPaths(root=root)
    paths.ensure_dirs()

    progress = ManifestProgress(paths.progress_db)

    if overwrite:
        logger.warning("Overwrite=True -> resetting manifest progress")
        progress.reset()

        # Optionally remove old outputs too
        # (we keep it simple and only reset progress)
        # You can uncomment if you want a full wipe:
        # for p in [paths.events, paths.stations, paths.picks, paths.stats]:
        #     if p.exists():
        #         p.unlink()

    local_networks = list_local_networks(data_type="bank").keys()
    local_networks = list(local_networks)

    logger.info("Found %d local networks: %s", len(local_networks), local_networks)

    if not local_networks:
        raise ValueError("No networks found to build manifests.")

    if include_manual_network_info is None and include_networks:
        path = root / HF_CONFIG["networks"].path
        include_manual_network_info = pd.read_parquet(path )


    for net in local_networks:

        if networks is not None and net not in networks:
            logger.info("Skipping network %s (not in specified networks)", net)
            continue

        logger.info("Processing network: %s", net)
        print(net)

        net_paths = get_utdq_paths(net)
        bank = UTDQBank(net_paths["bank"])

        if include_networks and not progress.is_done("stats", net):
            logger.info("Building stats manifest for %s", net)

            manual_info = include_manual_network_info[include_manual_network_info["network"] == net]
            summary = bank.get_summary()

            for key, value in summary.items():
                manual_info[key] = value

            df_summary = sanitize_dataframe_for_parquet(manual_info,
                                                       string_cols=PREF_NETWORK_TYPES["string_cols"],
                                                       float_cols=PREF_NETWORK_TYPES["float_cols"],
                                                       int_cols=PREF_NETWORK_TYPES["int_cols"],
                                                       datetime_cols=PREF_NETWORK_TYPES["datetime_cols"],
                                                       bool_cols=PREF_NETWORK_TYPES["bool_cols"])

            existing_pref = [c for c in PREF_NETWORK_ORDER if c in df_summary.columns]
            remaining = [c for c in df_summary.columns if c not in existing_pref]
            df_summary = df_summary[existing_pref + remaining]

            _append_parquet_dedup(paths.network, df_summary, subset_cols=["network"])

            progress.mark_done("network", net)

    logger.info("Manifest build complete.")
    return paths
        
            


        # paths.get_events(net).mkdir(parents=True, exist_ok=True)
        # paths.get_stations(net).mkdir(parents=True, exist_ok=True)
        # paths.get_picks(net).mkdir(parents=True, exist_ok=True)

        # net_paths = get_utdq_paths(net)
        # bank = UTDQBank(net_paths["bank"])
        # df_events = bank.read_index().copy()

        # if apply_utd_qc:
        #     logger.info("Applying UTD QC.")
        #     cat = bank.get_events(event_id=chunk)
        #     cat.apply_utdq_qc(debug=qc_debug, inplace=True)

        # if include_events and not progress.is_done("events", net):
        #     logger.info("Building events manifest for %s", net)
        #     df_events["network"] = net

