"""
Convert a local UTDQuake root from the pre-1.0 layout to the 1.0 layout.

Before 1.0, ``network`` named the UTDQuake network in every table and file
(``events/network=tx.parquet``), and in the stations and picks tables it
replaced the FDSN code of the station. From 1.0:

- ``utdq_net`` names the UTDQuake network: the key of the network table and of
  every file (``events/utdq_net=tx.parquet``).
- ``network`` is the FDSN code of the station, in the stations table (read
  from the station database path, ``.../.{NET}_{STA}.db``) and in the picks
  table (read from ``seed_id``), fixed by
  :func:`utdquake.qc.stations.resolve_station_networks`.
- the events ``stations`` column lists ``NET.STA`` codes.
- the events and network tables get the picks per phase label (``p_count``,
  ``pg_count``, ...) and per family (``p_arrivals``, ``s_arrivals``: every
  P-type / S-type pick), counted from the picks table.
- the network table gets ``catalog``, ``catalog_type``, ``networks`` (the
  FDSN codes of its stations, most picks first) and ``dataset_version``, and
  its station counts are recomputed from the new stations table.

The source root is only read. Banks are not touched (they do not depend on
the UTDQuake network name): copy them separately.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from ..core.config import get_hf_entry
from ..qc.stations import event_stations, resolve_station_networks
from ..utils.utils import add_phase_counts, get_network_summary
from .schema import (PHASE_COUNT_COLS, PREF_EVENTS_ORDER, PREF_EVENTS_TYPES, PREF_NETWORK_ORDER,
                     PREF_NETWORK_TYPES, PREF_PICKS_ORDER, PREF_PICKS_TYPES,
                     PREF_STATIONS_ORDER, PREF_STATIONS_TYPES, sanitize_dataframe)

logger = logging.getLogger(__name__)

OLD_PREFIX = "network="
STATION_DB_RE = r"/\.([^/_]+)_([^/]*)\.db$"   # .../.{NET}_{STA}.db, DAS: .../.{NET}_{STA}_{CHA}.db
STATION_COUNT_COLS = ["total_stations", "located_stations", "confirmed_stations", "calculated_stations"]


def _old_path(root: Path, key: str, name: str, das: bool) -> Path:
    path = get_hf_entry(key, das).path.replace("utdq_net={utdq_net}", OLD_PREFIX + "{utdq_net}")
    return root / path.format(utdq_net=name)


def _new_path(root: Path, key: str, utdq_net: str, das: bool) -> Path:
    return root / get_hf_entry(key, das).path.format(utdq_net=utdq_net)


def _old_names(root: Path, das: bool) -> list[str]:
    folder = _old_path(root, "events", "x", das).parent
    return sorted(p.stem[len(OLD_PREFIX):] for p in folder.glob(f"{OLD_PREFIX}*.parquet"))


def _write(df: pd.DataFrame, path: Path, types: dict, order: list) -> None:
    df = sanitize_dataframe(df, order_cols=order, **types)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def migrate_network(src: Path, dst: Path, old: str, new: str, das: bool = False) -> dict:
    """Convert one UTDQuake network's events, stations and picks; return a report."""
    events = pd.read_parquet(_old_path(src, "events", old, das))
    stations = pd.read_parquet(_old_path(src, "stations", old, das))
    picks = pd.read_parquet(_old_path(src, "picks", old, das))
    n_events, n_picks = len(events), len(picks)

    # FDSN code of each station row, from its station database file name
    fdsn = stations["db_path"].astype("string").str.extract(STATION_DB_RE)
    station = stations["station"].astype("string")
    bad = fdsn[1].ne(station).fillna(True)
    if das:  # DAS databases are per channel (.{NET}_{STA}_{CHA}.db), a few per station
        bad &= fdsn[1].ne(station + "_" + stations["channel"].astype("string")).fillna(True)
    if bad.any():
        logger.warning("[%s] %d station rows without a usable db_path, dropped (their picks get "
                       "rows without location): %s", old, bad.sum(),
                       stations.loc[bad, ["station", "db_path"]].to_dict("records"))
    stations = stations[~bad].copy()
    stations["network"] = fdsn.loc[~bad, 0].values
    stations["db_path"] = stations["db_path"].str.replace(rf"^{re.escape(old)}/", f"{new}/", regex=True)

    stations, picks, report = resolve_station_networks(stations, picks.drop(columns=["network"]), das=das)
    events = events.drop(columns=["network", "stations", "path"], errors="ignore")
    events = events.merge(event_stations(picks), left_on="event_id", right_index=True, how="left")
    events = add_phase_counts(events, picks)
    for df in (events, stations, picks):
        df.insert(0, "utdq_net", new)

    assert len(events) == n_events and len(picks) == n_picks
    _write(events, _new_path(dst, "events", new, das), PREF_EVENTS_TYPES, PREF_EVENTS_ORDER)
    _write(stations, _new_path(dst, "stations", new, das), PREF_STATIONS_TYPES, PREF_STATIONS_ORDER)
    _write(picks, _new_path(dst, "picks", new, das), PREF_PICKS_TYPES, PREF_PICKS_ORDER)

    for key, ext in ((".utdquake/travel_time", ".parquet"), (".utdquake/stats", ".npz")):
        src_file = src / get_hf_entry(key, das).path.format(utdq_net=old)
        if src_file.exists():
            dst_file = _new_path(dst, key, new, das)
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    networks = picks.groupby("network").size().sort_values(ascending=False, kind="stable")
    summary = get_network_summary(stations=stations, events=events, das=das, picks=picks)
    return {"old": old, "utdq_net": new, "events": n_events, "picks": n_picks,
            "station_rows": len(stations), "networks": ",".join(networks.index),
            **report, **{c: summary[c] for c in STATION_COUNT_COLS},
            "summary_events": summary["events"],
            **{c: summary[c] for c in PHASE_COUNT_COLS}}


def migrate_root(
    src: Path,
    dst: Path,
    renames: Optional[Dict[str, str]] = None,
    catalogs: Optional[Dict[str, dict]] = None,
    das: bool = False,
    only: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """
    Convert every UTDQuake network of a pre-1.0 root ``src`` into ``dst``.

    Parameters
    ----------
    src, dst : Path
        Pre-1.0 root to read and 1.0 root to write (must differ).
    renames : dict, optional
        ``{old name: utdq_net}`` for networks that get a new code; the rest
        keep their name.
    catalogs : dict, optional
        ``{utdq_net: {column: value}}`` for the new network-table columns
        (``catalog``, ``catalog_type``, ``dataset_version``) and any other
        column to set or add, e.g. a row for a network missing from the table.
    das : bool, optional
        Convert the DAS part of the root. Default False.
    only : iterable of str, optional
        Old names to convert; default all.

    Returns
    -------
    pd.DataFrame
        One report row per converted network.

    Notes
    -----
    The rows of the converted networks are updated or appended in ``dst``'s
    network table; rows of other networks already there are kept, so a root
    with a single new network (e.g. a fresh build) can be migrated into an
    existing 1.0 root.
    """
    src, dst = Path(src).resolve(), Path(dst).resolve()
    if src == dst:
        raise ValueError("src and dst must differ: the source root is never modified")
    renames, catalogs = renames or {}, catalogs or {}

    rows = []
    for old in _old_names(src, das):
        if only is not None and old not in only:
            continue
        new = renames.get(old, old)
        logger.info("Migrating %s -> %s", old, new)
        rows.append(migrate_network(src, dst, old, new, das=das))
    report = pd.DataFrame(rows)

    # --- network table ---
    table = pd.read_parquet(src / get_hf_entry("networks", das).path)
    table = table.rename(columns={"network": "utdq_net"})
    table["utdq_net"] = table["utdq_net"].replace(renames)
    if only is not None:
        table = table[table["utdq_net"].isin(report["utdq_net"])]
    for utdq_net in report["utdq_net"]:
        if utdq_net not in set(table["utdq_net"]):
            logger.warning("%s has files but no row in the network table: adding one", utdq_net)
            table = pd.concat([table, pd.DataFrame({"utdq_net": [utdq_net]})], ignore_index=True)

    counts = report.set_index("utdq_net")
    for col in STATION_COUNT_COLS + ["networks"]:
        table[col] = table["utdq_net"].map(counts[col])
    # picks per phase label and family, from the converted picks table
    for col in PHASE_COUNT_COLS:
        table[col] = table["utdq_net"].map(counts[col])
    # events after QC: keep the table's value, fill it where missing
    filled = table["utdq_net"].map(counts["summary_events"])
    table["events"] = table["events"].fillna(filled) if "events" in table else filled
    for utdq_net, values in catalogs.items():
        for col, value in values.items():
            if col not in table:
                table[col] = pd.NA
            table.loc[table["utdq_net"] == utdq_net, col] = value

    # update-or-append: rows of other networks already in dst are kept
    table_path = dst / get_hf_entry("networks", das).path
    if table_path.exists():
        existing = pd.read_parquet(table_path)
        table = pd.concat([existing[~existing["utdq_net"].isin(table["utdq_net"])], table],
                          ignore_index=True)
    _write(table, table_path, PREF_NETWORK_TYPES, PREF_NETWORK_ORDER)
    return report
