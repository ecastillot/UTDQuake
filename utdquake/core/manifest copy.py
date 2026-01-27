from __future__ import annotations

import os
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Dict, List

import pandas as pd

from utdquake.bank.bank import EventBank
from utdquake.core.cache import (
    get_root,
    list_local_networks,
    list_remote_networks,
    get_eventbank_path,
)
from utdquake.core.config import (PREF_PICKS_ORDER,PREF_EVENTS_ORDER,
                                  PREF_STATIONS_ORDER,PREF_STATS_ORDER)
from utdquake.core.download import download_utdquake

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class ManifestPaths:
    """
    Centralized manifest paths for UTDQuake.

    Layout:

    root/
      manifests/
        events.parquet
        stations.parquet
        picks.parquet
        stats.parquet
        progress.sqlite
    """

    root: Path
    manifest_dirname: str = "manifests"

    events_name: str = "events.parquet"
    stations_name: str = "stations.parquet"
    picks_name: str = "picks.parquet"
    stats_name: str = "stats.parquet"

    progress_name: str = "progress.sqlite"

    @property
    def manifest_dir(self) -> Path:
        return self.root / self.manifest_dirname

    @property
    def events(self) -> Path:
        return self.manifest_dir / self.events_name

    @property
    def stations(self) -> Path:
        return self.manifest_dir / self.stations_name

    @property
    def picks(self) -> Path:
        return self.manifest_dir / self.picks_name

    @property
    def stats(self) -> Path:
        return self.manifest_dir / self.stats_name

    @property
    def progress_db(self) -> Path:
        return self.manifest_dir / self.progress_name

    def ensure_dirs(self) -> None:
        self.manifest_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Progress tracker (resume-safe)
# ---------------------------------------------------------------------
class ManifestProgress:
    """
    Tracks which networks were already processed for each manifest type.

    This avoids duplicates and supports resume after interruption.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS progress (
                    manifest TEXT NOT NULL,
                    network TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (manifest, network)
                )
                """
            )

    def is_done(self, manifest: str, network: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT status FROM progress WHERE manifest=? AND network=?",
                (manifest, network),
            )
            row = cur.fetchone()
        return row is not None and row[0] == "done"

    def mark_done(self, manifest: str, network: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO progress (manifest, network, status)
                VALUES (?, ?, 'done')
                ON CONFLICT(manifest, network)
                DO UPDATE SET status='done', updated_at=CURRENT_TIMESTAMP
                """,
                (manifest, network),
            )

    def reset(self, manifest: Optional[str] = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            if manifest is None:
                conn.execute("DELETE FROM progress")
            else:
                conn.execute("DELETE FROM progress WHERE manifest=?", (manifest,))


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _safe_concat(existing: Optional[pd.DataFrame], new: pd.DataFrame) -> pd.DataFrame:
    if existing is None or existing.empty:
        return new
    return pd.concat([existing, new], ignore_index=True)


def _load_eventbank(network: str, force_download: bool) -> EventBank:
    path = get_eventbank_path(network)

    if not path.exists():
        if force_download:
            logger.info("Downloading missing network %s...", network)
            download_utdquake(local_dir=get_root() / "events", networks=[network])
        else:
            raise FileNotFoundError(f"Network not found locally: {network}")

    return EventBank(str(path))


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

def sanitize_dataframe_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make DataFrame safe for Parquet + HuggingFace:
    - No NaNs in numeric columns
    - No None in object columns
    - Stable dtypes across shards
    """
    df = df.copy()

    # ---- normalize column names ----
    df.columns = df.columns.str.lower()
    df.columns = df.columns.str.replace(r"\s+", "_", regex=True)

    # ---- floats ----
    float_cols = df.select_dtypes(include=["float"]).columns
    for c in float_cols:
        if df[c].isna().any():
            df[c] = df[c].fillna(-9999.0)

    # ---- integers (optional but recommended) ----
    int_cols = df.select_dtypes(include=["int", "Int64"]).columns
    for c in int_cols:
        if df[c].isna().any():
            df[c] = df[c].astype("float").fillna(-9999).astype("int64")

    # ---- booleans ----
    bool_cols = df.select_dtypes(include=["bool", "boolean"]).columns
    for c in bool_cols:
        if df[c].isna().any():
            df[c] = df[c].fillna(False)

    # ---- objects / strings ----
    obj_cols = df.select_dtypes(include=["object"]).columns
    for c in obj_cols:
        if df[c].isna().any():
            df[c] = df[c].fillna("")

    # ---- datetimes: leave NaT alone ----
    return df

# ---------------------------------------------------------------------
# Main manifest builder
# ---------------------------------------------------------------------
def build_manifests(
    networks: Optional[Iterable[str]] = None,
    force_download: bool = False,
    overwrite: bool = False,
    include_events: bool = True,
    include_stations: bool = True,
    include_picks: bool = True,
    include_stats: bool = True,
    per_network_shards: bool = True,
    include_manual_network_info: pd.DataFrame = None
) -> ManifestPaths:
    """
    Build UTDQuake manifest files incrementally, resume-safe.

    Key ideas:
    - process one network at a time
    - save output after each network
    - track progress in SQLite so you can resume safely
    - optional per-network shards to avoid huge RAM usage

    Parameters
    ----------
    networks
        Networks to process. If None, uses local networks.
    force_download
        If True, download missing networks.
    overwrite
        If True, delete progress and rebuild from scratch.
    include_events, include_stations, include_picks, include_stats
        Which manifests to build.
    per_network_shards
        If True, saves one parquet per network per manifest type, e.g.
        manifests/events/network=tx.parquet
        manifests/picks/network=tx.parquet

        This is the best option for very large datasets.
        You can still combine later if you want.

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

    if networks is None:
        networks = list_local_networks()

    networks = list(networks)
    if not networks:
        raise ValueError("No networks found to build manifests.")

    # -----------------------------------------------------------------
    # output locations
    # -----------------------------------------------------------------
    shard_dirs: Dict[str, Path] = {
        "events": paths.manifest_dir / "events",
        "stations": paths.manifest_dir / "stations",
        "picks": paths.manifest_dir / "picks",
        "stats": paths.manifest_dir / "stats",
    }

    for d in shard_dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # build loop
    # -----------------------------------------------------------------
    for net in networks:
        logger.info("Processing network: %s", net)

        bank = _load_eventbank(net, force_download=force_download)

        # ------------------ EVENTS ------------------
        if include_events and not progress.is_done("events", net):
            logger.info("Building events manifest for %s", net)
            df_events = bank.read_index().copy()
            df_events["network"] = net

            df_events = sanitize_dataframe_for_parquet(df_events)

            existing_pref = [c for c in PREF_EVENTS_ORDER if c in df_events.columns]
            remaining = [c for c in df_events.columns if c not in existing_pref]
            df_events = df_events[existing_pref + remaining]

            if per_network_shards:
                out = shard_dirs["events"] / f"network={net}.parquet"
                _write_parquet_atomic(df_events, out)
            else:
                # combined file (can become heavy)
                _append_parquet_dedup(
                    paths.events,
                    df_events,
                    subset_cols=["network", "event_id"] if "event_id" in df_events.columns else ["network"],
                )

            progress.mark_done("events", net)

        # ------------------ STATIONS ------------------
        if include_stations and not progress.is_done("stations", net):
            logger.info("Building stations manifest for %s", net)
            df_sta = bank.get_stations().copy()
            df_sta["network"] = net

            df_sta = sanitize_dataframe_for_parquet(df_sta)

            existing_pref = [c for c in PREF_STATIONS_ORDER if c in df_sta.columns]
            remaining = [c for c in df_sta.columns if c not in existing_pref]
            df_sta = df_sta[existing_pref + remaining]

            if per_network_shards:
                out = shard_dirs["stations"] / f"network={net}.parquet"
                _write_parquet_atomic(df_sta, out)
            else:
                subset = ["network"]
                for c in ["station", "station_code", "id", "seed_id"]:
                    if c in df_sta.columns:
                        subset.append(c)
                        break
                _append_parquet_dedup(paths.stations, df_sta, subset_cols=subset)

            progress.mark_done("stations", net)

        # ------------------ PICKS ------------------
        if include_picks and not progress.is_done("picks", net):
            logger.info("Building picks manifest for %s", net)

            # EventBank method you said exists:
            # df_picks = bank.load_picks()
            df_picks = bank.load_picks().copy()
            df_picks["network"] = net
            df_picks["travel_time"] = (df_picks["time"] - df_picks["origin_time"]).dt.total_seconds()

            df_picks = sanitize_dataframe_for_parquet(df_picks)

            existing_pref = [c for c in PREF_PICKS_ORDER if c in df_picks.columns]
            remaining = [c for c in df_picks.columns if c not in existing_pref]
            df_picks = df_picks[existing_pref + remaining]


            if per_network_shards:
                out = shard_dirs["picks"] / f"network={net}.parquet"

                df_picks = sanitize_dataframe_for_parquet(df_picks)

                _write_parquet_atomic(df_picks, out)
            else:
                subset = ["network"]
                # typical unique pick keys (best-effort)
                for c in ["pick_id", "id", "resource_id"]:
                    if c in df_picks.columns:
                        subset.append(c)
                        break
                _append_parquet_dedup(paths.picks, df_picks, subset_cols=subset)

            progress.mark_done("picks", net)

        # ------------------ STATS ------------------
        if include_stats and not progress.is_done("stats", net):
            logger.info("Building stats manifest for %s", net)
            df_stats = pd.DataFrame([bank.stats])
            df_stats["network"] = net

            if include_manual_network_info is not None:
                df_stats = pd.merge(df_stats,include_manual_network_info,
                                    on="network",how="left")
                
            df_stats = sanitize_dataframe_for_parquet(df_stats)

            existing_pref = [c for c in PREF_STATS_ORDER if c in df_stats.columns]
            remaining = [c for c in df_stats.columns if c not in existing_pref]
            df_stats = df_stats[existing_pref + remaining]


            # if per_network_shards:
            #     out = shard_dirs["stats"] / f"network={net}.parquet"
            #     _write_parquet_atomic(df_stats, out)
            # else:
            _append_parquet_dedup(paths.stats, df_stats, subset_cols=["network"])

            progress.mark_done("stats", net)

    logger.info("Manifest build complete.")
    return paths


# ---------------------------------------------------------------------
# Convenience: combine shards into single parquet (optional)
# ---------------------------------------------------------------------
def combine_manifest_shards(paths: ManifestPaths) -> None:
    """
    Combine per-network shard parquet files into single parquet files.

    WARNING: this may use lots of RAM if your dataset is huge.
    Use only if you really need a single file per manifest type.
    """
    for manifest_name in ["events", "stations", "picks", "stats"]:
        shard_dir = paths.manifest_dir / manifest_name
        out_file = getattr(paths, manifest_name)

        shard_files = sorted(shard_dir.glob("network=*.parquet"))
        if not shard_files:
            logger.warning("No shards found for %s", manifest_name)
            continue

        logger.info("Combining %d shards into %s", len(shard_files), out_file.name)
        dfs = [pd.read_parquet(f) for f in shard_files]
        combined = pd.concat(dfs, ignore_index=True)
        _write_parquet_atomic(combined, out_file)
