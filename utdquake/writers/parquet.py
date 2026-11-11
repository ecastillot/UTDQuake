from __future__ import annotations

import os
import logging
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Dict

import pandas as pd

from ..core.config import get_hf_entry,get_root,get_utdq_paths
from ..utils.cache import list_local_networks
from ..bank.bank import UTDQBank
from ..bank.utils import preferred_origins_from_files
from ..core.utils import renamed_kwarg
from ..qc.stations import event_stations, resolve_station_networks
from ..utils.utils import add_phase_counts, get_network_summary
from .manifest import ManifestPaths, ManifestProgress
from .schema import (PREF_PICKS_ORDER,
                    PREF_PICKS_TYPES,
                    PREF_EVENTS_ORDER,
                    PREF_EVENTS_TYPES,
                    PREF_NETWORK_ORDER,
                    PREF_NETWORK_TYPES,
                    PREF_STATIONS_ORDER,
                    PREF_STATIONS_TYPES,
                    missing_network_info,
                    sanitize_dataframe)

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


def _event_versions(events_manifest: Path, manual_info: Optional[pd.DataFrame], utdq_net: str) -> tuple:
    """
    ``dataset_version`` of the events of a network.

    Returns ``(known, version)``: ``known`` maps the event_id of each event
    already in ``events_manifest`` to its version (kept as is), ``version``
    is the one for new events, the network's ``dataset_version`` in
    ``manual_info``. Events added to an existing network by a later release
    so get a different version from the earlier ones.
    """
    known = {}
    if events_manifest.exists():
        previous = pd.read_parquet(events_manifest)
        if "dataset_version" in previous:
            known = previous.dropna(subset=["dataset_version"]).set_index("event_id")["dataset_version"].to_dict()
    version = None
    if manual_info is not None and "dataset_version" in manual_info:
        rows = manual_info.loc[manual_info["utdq_net"] == utdq_net, "dataset_version"].dropna()
        version = rows.iloc[0] if len(rows) else None
    if version is None:
        # not given: the release the new events go into (latest released version + one minor version)
        from ..core.config import next_dataset_version
        version = next_dataset_version()
        if version is None:
            raise ValueError(f"[{utdq_net}] dataset_version not given and the released versions could not be "
                             "read from the Hub (offline?): pass it in include_manual_network_info, e.g. 'v2.1'.")
        logger.info("[%s] new events labelled dataset_version=%s (the next release)", utdq_net, version)
    return known, version


def build_manifests(
    utdq_nets: Optional[Iterable[str]] = None,
    das: bool = False,
    # force_download: bool = False,
    include_events: bool = False,
    include_stations: bool = False,
    include_picks: bool = False,
    include_networks: bool = True,
    overwrite: bool = False,
    per_network_shards: bool = True,
    include_manual_network_info: pd.DataFrame = None,
    networks: Optional[Iterable[str]] = None,
    ) -> ManifestPaths:
    """
    Build UTDQuake manifest files incrementally, resume-safe.

    Key ideas:
    - process one network at a time
    - save output after each network
    - track progress in SQLite so you can resume safely
    - saves one parquet per network per manifest type, e.g.
        manifests/events/utdq_net=tx.parquet
        manifests/picks/utdq_net=tx.parquet
    - stations and picks get the FDSN code of each station in ``network``,
      fixed by :func:`utdquake.qc.stations.resolve_station_networks`

    Parameters
    ----------
    utdq_nets
        UTDQuake networks to process. If None, uses local networks.
    force_download
        If True, download missing networks.
    overwrite
        If True, delete progress and rebuild from scratch.
    include_events, include_stations, include_picks, include_networks
        Which manifests to build.
    per_network_shards
        If True, saves one parquet per network per manifest type, e.g.
        manifests/events/utdq_net=tx.parquet
        manifests/picks/utdq_net=tx.parquet

        This is the best option for very large datasets.
        You can still combine later if you want.
    include_manual_network_info
        Per-network metadata that can't be derived from picks/events, keyed
        by a ``"utdq_net"`` column -- e.g. ``catalog``, ``catalog_type``,
        ``dataset_version``, ``provider``, ``provider_url``,
        ``country``, ``agency``, ``continent``, ``score``, and the
        contributor-provenance fields ``uploaded_by_github``,
        ``contact_email``, ``doi`` (see :ref:`upload-dataset-section`).
        ``uploaded_by_github`` should be a GitHub profile URL (e.g.
        ``"https://github.com/ecastillot"``), not a free-text name --
        that's what makes it possible to trace a network back to who
        actually contributed it. Rows are matched to each network by the
        ``"utdq_net"`` column; missing columns are left null. If None (the
        default) and ``include_networks`` is True, this is auto-loaded
        from the existing local ``network/network.parquet`` so
        previously-supplied manual info carries forward automatically --
        pass a DataFrame explicitly for a brand-new network, or the manual
        fields will all be null for it.
    networks
        Deprecated alias of ``utdq_nets``.

    Returns
    -------
    ManifestPaths
    """
    networks = renamed_kwarg(utdq_nets, networks, "utdq_nets", "networks", "build_manifests")

    root = get_root(das=das)
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

    local_networks = list_local_networks(data_type="bank",das=das).keys()
    local_networks = list(local_networks)

    logger.info("Found %d local networks: %s", len(local_networks), local_networks)

    if not local_networks:
        raise ValueError("No networks found to build manifests.")

    if include_manual_network_info is None and include_networks:
        try:
            path = root / get_hf_entry("networks", das=das).path
            include_manual_network_info = pd.read_parquet(path )
        except Exception as e:
            logger.warning("Could not load manual network info from %s: %s", path, e)
            include_manual_network_info = None
    if include_manual_network_info is not None:
        # a network without dataset_version goes into the next release (latest released version + 0.1)
        info = include_manual_network_info.copy()
        if "dataset_version" not in info:
            info["dataset_version"] = None
        empty = info["dataset_version"].isna() | (info["dataset_version"].astype(str).str.strip() == "")
        if empty.any():
            from ..core.config import next_dataset_version
            nxt = next_dataset_version()
            if nxt is not None:
                info.loc[empty, "dataset_version"] = nxt
                logger.info("dataset_version not given for %s: %s (the next release)",
                            info.loc[empty, "utdq_net"].tolist(), nxt)
        include_manual_network_info = info

    shard_dirs: Dict[str, Path] = {
        "events": paths.manifest_dir / "events",
        "stations": paths.manifest_dir / "stations",
        "picks": paths.manifest_dir / "picks",
        "networks": paths.manifest_dir / "network",
    }

    for d in shard_dirs.values():
        d.mkdir(parents=True, exist_ok=True)


    for net in local_networks:

        if networks is not None and net not in networks:
            logger.info("Skipping network %s (not in specified networks)", net)
            continue

        logger.info("Processing network: %s", net)

        net_paths = get_utdq_paths(net,das=das)
        logger.info("Loading bank for network %s from %s", net, net_paths["banks"])
        bank = UTDQBank(net_paths["banks"],
                        path_structure='{year}/{month}/{day}',
                        name_structure='{event_id_end}',
                        format='quakeml',
                        das=das)

        todo = {key: flag and not progress.is_done(key, net)
                for key, flag in (("events", include_events), ("stations", include_stations),
                                  ("picks", include_picks), ("networks", include_networks))}
        if not any(todo.values()):
            continue

        # Stations and picks are fixed together: ``network`` becomes the FDSN
        # code of each station (from the pick's seed_id), IR placeholder codes
        # are resolved where possible and every picked station gets a row.
        df_stations = bank.load_stations().copy()
        try:
            df_picks = bank.load_picks().copy()
        except FileNotFoundError:
            logger.warning("No picks index for %s yet; stations are not checked against picks", net)
            df_picks = None
        if df_picks is not None:
            df_stations, df_picks, report = resolve_station_networks(df_stations, df_picks, das=das)
        else:
            df_stations["network_source"] = "reported"
        for df in (df_stations, df_picks):
            if df is not None:
                df["utdq_net"] = net

        known_versions, new_version = _event_versions(shard_dirs["events"] / f"utdq_net={net}.parquet",
                                                      include_manual_network_info, net)
        if df_picks is not None:
            # object dtype: event_id may be an Arrow string column, whose map() result
            # cannot be filled with a string
            df_picks["dataset_version"] = df_picks["event_id"].astype(object).map(known_versions).fillna(new_version)

        #Events
        if todo["events"]:
            logger.info("Building events manifest for %s", net)
            df_events = bank.read_index().copy()
            df_events["utdq_net"] = net
            df_events["dataset_version"] = df_events["event_id"].astype(object).map(known_versions).fillna(new_version)

            # stations: comma-joined NET.STA codes of the stations that picked
            # each event (from the fixed picks above).
            df_events = df_events.drop(columns=["stations"], errors="ignore")
            if df_picks is not None:
                df_events = df_events.merge(event_stations(df_picks), left_on="event_id",
                                            right_index=True, how="left")
                # picks per phase label and family (p_count, ..., p_arrivals, s_arrivals)
                df_events = add_phase_counts(df_events, df_picks)
            else:
                df_events["stations"] = None

            # preferred_origin_id, read from the QuakeML files: building ObsPy
            # events for the whole bank does not scale (millions of events)
            preferred_df = preferred_origins_from_files(bank.bank_path, df_events["path"],
                                                        workers=min(16, os.cpu_count() or 1))
            df_events = df_events.merge(preferred_df, on="event_id", how="left")

            # Drop obsplus's internal "path" column - redundant since the
            # bank itself is the file-path lookup; not part of our schema.
            df_events = df_events.drop(columns=["path"], errors="ignore")

            df_events = sanitize_dataframe(df_events,
                                            string_cols=PREF_EVENTS_TYPES["string_cols"],
                                            float_cols=PREF_EVENTS_TYPES["float_cols"],
                                            int_cols=PREF_EVENTS_TYPES["int_cols"],
                                            datetime_cols=PREF_EVENTS_TYPES["datetime_cols"],
                                            bool_cols=PREF_EVENTS_TYPES["bool_cols"],
                                            order_cols=PREF_EVENTS_ORDER
                                            )

            if per_network_shards:
                out = shard_dirs["events"] / f"utdq_net={net}.parquet"
                _write_parquet_atomic(df_events, out)
            else:
                # combined file (can become heavy)
                path = shard_dirs["events"] / f"events.parquet"
                _append_parquet_dedup(
                    path,
                    df_events,
                    subset_cols=["utdq_net", "event_id"] if "event_id" in df_events.columns else ["utdq_net"],
                )

            progress.mark_done("events", net)
        
        # Stations
        if todo["stations"]:
            logger.info("Building stations manifest for %s", net)

            df_stations = sanitize_dataframe(df_stations,
                                            string_cols=PREF_STATIONS_TYPES["string_cols"],
                                            float_cols=PREF_STATIONS_TYPES["float_cols"],
                                            int_cols=PREF_STATIONS_TYPES["int_cols"],
                                            datetime_cols=PREF_STATIONS_TYPES["datetime_cols"],
                                            bool_cols=PREF_STATIONS_TYPES["bool_cols"],
                                            order_cols=PREF_STATIONS_ORDER)

            if per_network_shards:
                out = shard_dirs["stations"] / f"utdq_net={net}.parquet"
                _write_parquet_atomic(df_stations, out)
            else:
                path = shard_dirs["events"] / f"stations.parquet"
                subset = ["utdq_net", "network", "station"] + (["channel"] if das else [])
                _append_parquet_dedup(path, df_stations, subset_cols=subset)

            progress.mark_done("stations", net)   
            

        # Picks
        if todo["picks"] and df_picks is not None:
            logger.info("Building picks manifest for %s", net)

            df_picks = sanitize_dataframe(df_picks,
                                    string_cols=PREF_PICKS_TYPES["string_cols"],
                                    float_cols=PREF_PICKS_TYPES["float_cols"],
                                    int_cols=PREF_PICKS_TYPES["int_cols"],
                                    datetime_cols=PREF_PICKS_TYPES["datetime_cols"],
                                    bool_cols=PREF_PICKS_TYPES["bool_cols"],
                                    order_cols=PREF_PICKS_ORDER)
            
            if per_network_shards:
                out = shard_dirs["picks"] / f"utdq_net={net}.parquet"

                _write_parquet_atomic(df_picks, out)
            else:
                path = shard_dirs["events"] / f"picks.parquet"
                subset = ["utdq_net"]
                # typical unique pick keys (best-effort)
                for c in ["pick_id", "id", "resource_id"]:
                    if c in df_picks.columns:
                        subset.append(c)
                        break
                _append_parquet_dedup(path, df_picks, subset_cols=subset)

            progress.mark_done("picks", net)

        

        if todo["networks"]:
            logger.info("Building networks manifest for %s", net)

            if include_manual_network_info is not None:
                manual_info = include_manual_network_info[include_manual_network_info["utdq_net"] == net].copy()
                if manual_info.empty:
                    manual_info = pd.DataFrame({"utdq_net": [net]})
            else:
                manual_info = pd.DataFrame({"utdq_net": [net]})

            summary = get_network_summary(stations=df_stations, events=bank.load_events(), das=das, picks=df_picks)

            for key, value in summary.items():
                manual_info[key] = value
            if df_picks is not None:
                by_net = df_picks.groupby("network").size().sort_values(ascending=False, kind="stable")
                manual_info["networks"] = ",".join(by_net.index)
            for problem in missing_network_info(manual_info.iloc[0]):
                logger.warning("[%s] %s: pass it in include_manual_network_info "
                               "(publish_network refuses networks without it)", net, problem)

            df_summary = sanitize_dataframe(manual_info,
                                            string_cols=PREF_NETWORK_TYPES["string_cols"],
                                            float_cols=PREF_NETWORK_TYPES["float_cols"],
                                            int_cols=PREF_NETWORK_TYPES["int_cols"],
                                            datetime_cols=PREF_NETWORK_TYPES["datetime_cols"],
                                            bool_cols=PREF_NETWORK_TYPES["bool_cols"],
                                            order_cols=PREF_NETWORK_ORDER)


            path = shard_dirs["networks"] / f"network.parquet"
            _append_parquet_dedup(path, df_summary, subset_cols=["utdq_net"])

            progress.mark_done("networks", net)

    logger.info("Manifest build complete.")
    return paths
        
            


        # paths.get_events(net).mkdir(parents=True, exist_ok=True)
        # paths.get_stations(net).mkdir(parents=True, exist_ok=True)
        # paths.get_picks(net).mkdir(parents=True, exist_ok=True)

        # net_paths = get_utdq_paths(net,das=das)
        # bank = UTDQBank(net_paths["bank"],das=das)
        # df_events = bank.read_index().copy()

        # if apply_utd_qc:
        #     logger.info("Applying UTD QC.")
        #     cat = bank.get_events(event_id=chunk)
        #     cat.apply_utdq_qc(debug=qc_debug, inplace=True)

        # if include_events and not progress.is_done("events", net):
        #     logger.info("Building events manifest for %s", net)
        #     df_events["network"] = net


def publish_flat_manifests(
    root: Optional[Path] = None,
    das: bool = False,
    networks: Optional[Iterable[str]] = None,
) -> List[Path]:
    """
    Copy the per-network shards built by :func:`build_manifests` (under
    ``root/.utdquake/export/manifests/...``) into the flat
    ``root/{events,stations,picks,network}/...`` layout that both
    :func:`utdquake.publish_network` and
    :func:`utdquake.core.data.download_snapshot` expect.

    Parameters
    ----------
    root : Path, optional
        Local UTDQuake root. Defaults to ``get_root(das=das)``.
    das : bool, optional
        Whether this is a DAS dataset. Default False.
    networks : iterable of str, optional
        ``utdq_net`` codes to flatten. If None, every network found under
        ``manifests/events``, ``manifests/stations`` or
        ``manifests/picks`` is flattened.

    Returns
    -------
    list of Path
        Destination paths that were written.
    """
    root = Path(root) if root is not None else get_root(das=das)
    manifest_dir = ManifestPaths(root=root).manifest_dir

    if networks is None:
        found = set()
        for key in ("events", "stations", "picks"):
            shard_dir = manifest_dir / key
            if shard_dir.exists():
                found.update(p.stem.split("=", 1)[-1] for p in shard_dir.glob("utdq_net=*.parquet"))
        networks = sorted(found)

    written: List[Path] = []
    for key in ("events", "stations", "picks"):
        for net in networks:
            src = manifest_dir / key / f"utdq_net={net}.parquet"
            if not src.exists():
                logger.warning("No %s manifest for network %s at %s; skipping.", key, net, src)
                continue
            dst = root / get_hf_entry(key, das).path.format(utdq_net=net)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.info("Published %s -> %s", key, dst)
            written.append(dst)

    network_src = manifest_dir / "network" / "network.parquet"
    if network_src.exists():
        network_dst = root / get_hf_entry("networks", das).path
        network_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(network_src, network_dst)
        logger.info("Published network -> %s", network_dst)
        written.append(network_dst)

    return written

