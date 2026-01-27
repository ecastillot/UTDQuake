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
                                  PREF_STATIONS_ORDER,PREF_STATS_ORDER,
                                  PREF_PICKS_TYPES,PREF_EVENTS_TYPES,
                                  PREF_STATIONS_TYPES,PREF_STATS_TYPES)

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

def sanitize_dataframe_for_parquet(
    df: pd.DataFrame,
    string_cols=None,
    float_cols=None,
    int_cols=None,
    datetime_cols=None,
    bool_cols=None,
    debug=False
) -> pd.DataFrame:
    """
    Safely sanitize a DataFrame for Parquet / Hugging Face Datasets.

    Args:
        df (pd.DataFrame): Input DataFrame
        string_cols (list[str], optional): Columns to force as strings
        float_cols (list[str], optional): Columns to force as floats
        int_cols (list[str], optional): Columns to force as integers
        datetime_cols (list[str], optional): Columns to force as datetime
        bool_cols (list[str], optional): Columns to force as boolean
        debug (bool): If True, prints DataFrame state at each step

    Returns:
        pd.DataFrame: Sanitized DataFrame
    """
    df = df.copy()
    
    if debug:
        print("Step 0: Original DataFrame")
        print(df.head(), "\n")
        print("Dtypes:", df.dtypes, "\n")
    
    # ---- 1. Normalize column names ----
    df.columns = df.columns.str.lower().str.replace(r"\s+", "_", regex=True)
    if debug:
        print("Step 1: Normalized column names")
        print(df.head(), "\n")
    
    # ---- 2. Parse datetime columns ----
    if datetime_cols:
        for c in datetime_cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    else:
        for c in df.select_dtypes(include=["object"]).columns:
            try:
                df[c] = pd.to_datetime(df[c], errors="ignore")
            except Exception:
                pass
    if debug:
        print("Step 2: After datetime conversion")
        print(df.head(), "\n")
    
    # ---- 3. Force float columns ----
    if float_cols:
        for c in float_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    if debug and float_cols:
        print(f"Step 3: Forced float columns: {float_cols}")
    
    # ---- 4. Force integer columns ----
    if int_cols:
        for c in int_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")  # nullable int
    if debug and int_cols:
        print(f"Step 4: Forced integer columns: {int_cols}")
    
    # ---- 5. Force string columns ----
    if string_cols:
        for c in string_cols:
            if c in df.columns:
                df[c] = df[c].astype("string")
    if debug and string_cols:
        print(f"Step 5: Forced string columns: {string_cols}")
    
    # ---- 6. Force boolean columns ----
    if bool_cols:
        for c in bool_cols:
            if c in df.columns:
                df[c] = df[c].astype("boolean")
    if debug and bool_cols:
        print(f"Step 6: Forced boolean columns: {bool_cols}")
    
    # ---- 7. Auto-handle remaining object columns ----
    for c in df.select_dtypes(include=["object"]).columns:
        df[c] = df[c].astype("string")
    
    # ---- 8. Numeric columns → float64 for Arrow safety ----
    for c in df.select_dtypes(include=["float64"]).columns:
        df[c] = df[c].astype("float64")

    for c in df.select_dtypes(include=["int64", "Int64"]).columns:
        df[c] = df[c].astype("Int64")
    
    # ---- 9. Boolean → nullable boolean (catch any remaining) ----
    for c in df.select_dtypes(include=["bool"]).columns:
        df[c] = df[c].astype("boolean")
    
    if debug:
        print("Step 7-9: Final DataFrame after sanitization")
        print(df.head(), "\n")
        print("Dtypes after sanitization:")
        print(df.dtypes)
    
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

            df_events = sanitize_dataframe_for_parquet(df_events,
                                                       string_cols=PREF_EVENTS_TYPES["string_cols"],
                                                       float_cols=PREF_EVENTS_TYPES["float_cols"],
                                                       int_cols=PREF_EVENTS_TYPES["int_cols"],
                                                       datetime_cols=PREF_EVENTS_TYPES["datetime_cols"],
                                                       bool_cols=PREF_EVENTS_TYPES["bool_cols"])

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

            df_sta = sanitize_dataframe_for_parquet(df_sta,
                                                    string_cols=PREF_STATIONS_TYPES["string_cols"],
                                                    float_cols=PREF_STATIONS_TYPES["float_cols"],
                                                    int_cols=PREF_STATIONS_TYPES["int_cols"],
                                                    datetime_cols=PREF_STATIONS_TYPES["datetime_cols"],
                                                    bool_cols=PREF_STATIONS_TYPES["bool_cols"])

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

            df_picks = sanitize_dataframe_for_parquet(df_picks,
                                                      string_cols=PREF_PICKS_TYPES["string_cols"],
                                                      float_cols=PREF_PICKS_TYPES["float_cols"],
                                                      int_cols=PREF_PICKS_TYPES["int_cols"],
                                                      datetime_cols=PREF_PICKS_TYPES["datetime_cols"],
                                                      bool_cols=PREF_PICKS_TYPES["bool_cols"])

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
                
            df_stats = sanitize_dataframe_for_parquet(df_stats,
                                                       string_cols=PREF_STATS_TYPES["string_cols"],
                                                       float_cols=PREF_STATS_TYPES["float_cols"],
                                                       int_cols=PREF_STATS_TYPES["int_cols"],
                                                       datetime_cols=PREF_STATS_TYPES["datetime_cols"],
                                                       bool_cols=PREF_STATS_TYPES["bool_cols"])

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
