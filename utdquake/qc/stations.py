"""
FDSN network codes of the stations and picks tables.

In the stations and picks tables, ``network`` is the FDSN code of the
recording station, as in the pick's ``seed_id``; together with ``utdq_net``
and ``station`` it is the key that links picks to stations. Two problems of
the source data are fixed here so that this key is clean:

- ISC reports some picks with the placeholder network code ``IR`` (its
  International Registry of stations) instead of the station's FDSN code, so
  one station can show up twice, e.g. as ``AV.ADAG`` and ``IR.ADAG``. An
  ``IR`` station is reassigned to its *twin* when exactly one station of the
  same UTDQuake network has the same station code, another network code, and
  a location within ``max_km`` of the ``IR`` station's calculated location.
  The two station rows are merged. Every other ``IR`` station keeps ``IR``.
- Picks whose station has no row in the stations table get a row without a
  location (``available``, ``confirmed`` and ``calculated`` False).

ISC station registry (run it every time an ISC-based network is built or
extended): ISC has no FDSN station service, so ``IR`` stations get no
location from the usual station download. The ISC registry
(http://www.isc.ac.uk/registries/download/station_csv.zip; a dated copy is
kept in ``.utdquake/isc_registry/`` of the dataset root) lists every IR
station's location and epochs, and FDSN networks too. A decisions table
(one row per ``(utdq_net, station)`` IR station: ``resolved_network``,
registry location; built by ``datasets/isc_ir/analyze_ir_stations.py`` from
the station code and the time span of its picks) is applied with
:func:`apply_ir_decisions`: the station gets its confirmed location from the
registry and, when exactly one FDSN network has the same code at the site
(within 10 km), that network. Keep the decisions: a later extension reuses
them and only decides new stations.

The pick's original ``seed_id`` is never changed. ``network_source`` says
where each ``network`` value comes from:

- ``reported``: the code reported with the pick.
- ``resolved_twin``: an ``IR`` pick reassigned to its twin's code.
- ``isc_registry``: an ``IR`` pick or station reassigned with the ISC registry.
- ``isc_registry_ir``: an ``IR`` station that the ISC registry knows only as
  ``IR`` (``IR`` is its code there); located from the registry.
- ``unresolved_ir``: an ``IR`` pick or station that could not be resolved.

Stations get ``ir_merged`` (True when an ``IR`` station row was merged in).
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

IR = "IR"
REPORTED = "reported"
RESOLVED_TWIN = "resolved_twin"
UNRESOLVED_IR = "unresolved_ir"
ISC_REGISTRY = "isc_registry"
ISC_REGISTRY_IR = "isc_registry_ir"


def seed_parts(seed_id: pd.Series) -> pd.DataFrame:
    """Split ``NET.STA.LOC.CHA`` seed ids into network, station, location and channel columns."""
    parts = seed_id.astype("string").str.split(".", n=3, expand=True)
    parts = parts.reindex(columns=range(4))
    parts.columns = ["network", "station", "location", "channel"]
    return parts


def _haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(x, dtype=float)) for x in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def _location(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Confirmed location, falling back to the calculated one."""
    lat = df["confirmed_latitude"].astype("Float64").fillna(df["calculated_latitude"].astype("Float64"))
    lon = df["confirmed_longitude"].astype("Float64").fillna(df["calculated_longitude"].astype("Float64"))
    return lat, lon


def ir_twins(stations: pd.DataFrame, max_km: float = 10.0) -> Dict[str, str]:
    """
    Return ``{station code: FDSN network code}`` for the ``IR`` stations of one
    UTDQuake network that can be reassigned to a twin (see module docstring).

    ``stations`` holds one row per (network, station), with the confirmed and
    calculated location columns.
    """
    ir = stations[stations["network"] == IR]
    others = stations[stations["network"] != IR]
    if ir.empty or others.empty:
        return {}

    ir_lat = ir["calculated_latitude"].astype("Float64")
    ir_lon = ir["calculated_longitude"].astype("Float64")
    ir_loc = pd.DataFrame({"station": ir["station"].values,
                           "ir_lat": ir_lat.values, "ir_lon": ir_lon.values}).dropna()

    lat, lon = _location(others)
    cand = pd.DataFrame({"station": others["station"].values, "twin": others["network"].values,
                         "lat": lat.values, "lon": lon.values}).dropna()

    pairs = ir_loc.merge(cand, on="station")
    if pairs.empty:
        return {}
    pairs["km"] = _haversine_km(pairs["ir_lat"], pairs["ir_lon"], pairs["lat"], pairs["lon"])
    close = pairs[pairs["km"] <= max_km]
    unique = close.groupby("station")["twin"].nunique()
    unique = unique[unique == 1].index
    close = close[close["station"].isin(unique)]
    return dict(zip(close["station"], close["twin"]))


def _pool(a: pd.Series, b: pd.Series, col: str) -> Tuple[float, float, int]:
    """Pool mean, std and count of the calculated ``col`` of two station rows
    (longitudes around the circle: the second mean is taken relative to the first)."""
    stats = []
    for row in (a, b):
        n = row.get("calculated_num_entries")
        n = 0 if pd.isna(n) else int(n)
        m = row.get(f"calculated_{col}")
        if n > 0 and not pd.isna(m):
            s = row.get(f"calculated_{col}_std")
            stats.append((n, float(m), 0.0 if pd.isna(s) else float(s)))
    if not stats:
        return np.nan, np.nan, 0
    if col == "longitude" and len(stats) > 1:
        ref = stats[0][1]
        stats = [(k, ref + ((m - ref + 180) % 360 - 180), s) for k, m, s in stats]
    n = sum(k for k, _, _ in stats)
    mean = sum(k * m for k, m, _ in stats) / n
    std = np.nan
    if n >= 2:
        ss = sum((k - 1) * s ** 2 + k * (m - mean) ** 2 for k, m, s in stats)
        std = float(np.sqrt(ss / (n - 1)))
    if col == "longitude":
        mean = (mean + 180) % 360 - 180
    return mean, std, n


def _merge_rows(twin: pd.Series, ir: pd.Series) -> pd.Series:
    """Merge an IR station row into its twin's row."""
    row = twin.copy()
    for flag in ("available", "calculated"):
        row[flag] = any(not pd.isna(r.get(flag)) and bool(r.get(flag)) for r in (twin, ir))
    lat, lat_std, n = _pool(twin, ir, "latitude")
    lon, lon_std, _ = _pool(twin, ir, "longitude")
    row["calculated_latitude"], row["calculated_latitude_std"] = lat, lat_std
    row["calculated_longitude"], row["calculated_longitude_std"] = lon, lon_std
    row["calculated_num_entries"] = n
    row["ir_merged"] = True
    return row


def resolve_station_networks(
    stations: pd.DataFrame,
    picks: pd.DataFrame,
    das: bool = False,
    max_km: float = 10.0,
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Fix the FDSN network codes of one UTDQuake network's stations and picks.

    Parameters
    ----------
    stations : pd.DataFrame
        Stations table of one UTDQuake network, with ``network`` holding the
        FDSN code (one row per network/station, or network/station/channel
        for DAS).
    picks : pd.DataFrame
        Picks table of the same network, with ``seed_id``.
    das : bool, optional
        DAS network: stations are keyed by channel too and IR codes do not
        occur, so only the missing station rows are added. Default False.
    max_km : float, optional
        Maximum distance between an IR station and its twin. Default 10 km.

    Returns
    -------
    stations, picks, report
        The fixed tables (``network``, ``station``, ``location``, ``channel``
        and ``network_source`` set in picks from the seed id; ``network_source``
        and ``ir_merged`` added to stations) and a dict of counts.
    """
    stations = stations.copy()
    picks = picks.copy()
    key = ["network", "station", "channel"] if das else ["network", "station"]

    parts = seed_parts(picks["seed_id"])
    for col in ("network", "station", "location", "channel"):
        picks[col] = parts[col].values
    reported_ir = picks["network"] == IR
    picks["network_source"] = np.where(reported_ir, UNRESOLVED_IR, REPORTED)

    stations["ir_merged"] = False
    twins = {} if das else ir_twins(stations, max_km=max_km)

    # --- merge each resolved IR station row into its twin's row ---
    if twins:
        by_key = {k: i for i, k in enumerate(zip(stations["network"], stations["station"]))}
        drop = []
        for code, net in twins.items():
            i_ir, i_twin = by_key[(IR, code)], by_key[(net, code)]
            stations.iloc[i_twin] = _merge_rows(stations.iloc[i_twin], stations.iloc[i_ir])
            drop.append(i_ir)
        stations = stations.drop(index=stations.index[drop])

        to_twin = reported_ir & picks["station"].isin(twins)
        picks.loc[to_twin, "network"] = picks.loc[to_twin, "station"].map(twins)
        picks.loc[to_twin, "network_source"] = RESOLVED_TWIN

    stations["network_source"] = np.where(stations["network"] == IR, UNRESOLVED_IR, REPORTED)

    # --- rows for stations that only appear in the picks ---
    pick_keys = picks[key + ["network_source"]].drop_duplicates(key)
    known = pd.MultiIndex.from_frame(stations[key].astype("string"))
    missing = pick_keys[~pd.MultiIndex.from_frame(pick_keys[key].astype("string")).isin(known)]
    if not missing.empty:
        add = missing.copy()
        add["network_source"] = np.where(add["network"] == IR, UNRESOLVED_IR, REPORTED)
        add["network_type"] = stations["network_type"].dropna().iloc[0] \
            if "network_type" in stations and stations["network_type"].notna().any() else "surface"
        for flag in ("available", "confirmed", "calculated", "ir_merged"):
            add[flag] = False
        add["calculated_num_entries"] = 0
        stations = pd.concat([stations, add], ignore_index=True)

    stations = stations.sort_values(key, ignore_index=True)
    assert not stations.duplicated(key).any(), "duplicate station keys after resolution"

    report = {
        "ir_stations": int((stations["network"] == IR).sum()) + len(twins),
        "ir_stations_resolved": len(twins),
        "ir_picks": int(reported_ir.sum()),
        "ir_picks_resolved": int((picks["network_source"] == RESOLVED_TWIN).sum()),
        "station_rows_added": int(len(missing)),
    }
    logger.info("Station network codes: %s", report)
    return stations, picks, report


def apply_ir_decisions(
    stations: pd.DataFrame,
    picks: pd.DataFrame,
    decisions: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Apply ISC registry decisions to the IR stations of one UTDQuake network.

    Parameters
    ----------
    stations, picks : pd.DataFrame
        Stations and picks tables of one (non-DAS) UTDQuake network, after
        :func:`resolve_station_networks`.
    decisions : pd.DataFrame
        Decisions for this network's IR stations: ``station``,
        ``resolved_network`` (``IR`` if not resolved), ``ir_lat``, ``ir_lon``,
        ``ir_elev`` (registry location, NaN if unknown) and ``ambiguous``
        (bool: 2+ FDSN networks at the site).

    Returns
    -------
    stations, picks, report
        Resolved IR stations take the FDSN network (merged into an existing
        row of that network if there is one, see ``ir_merged``); located IR
        stations get ``confirmed`` with the registry location unless their
        row already had a confirmed one. Picks of resolved stations get the
        network. Rows of picks are never added or removed; ``seed_id`` is
        kept.
    """
    stations = stations.copy()
    picks = picks.copy()
    dec = decisions.drop_duplicates("station").set_index("station")
    n_picks = len(picks)

    def locate(i, row):
        if pd.isna(row["ir_lat"]):
            return
        confirmed = stations.at[i, "confirmed"]
        if pd.isna(confirmed) or not bool(confirmed):  # keep a location confirmed by station metadata
            stations.at[i, "confirmed"] = True
            stations.at[i, "confirmed_latitude"] = row["ir_lat"]
            stations.at[i, "confirmed_longitude"] = row["ir_lon"]
            stations.at[i, "confirmed_elevation"] = row["ir_elev"]
        stations.at[i, "available"] = True

    by_key = {k: i for i, k in zip(stations.index, zip(stations["network"], stations["station"]))}
    drop, resolved, located_ir = [], {}, 0
    for code, row in dec.iterrows():
        i_ir = by_key.get((IR, code))
        if i_ir is None:
            continue
        net = row["resolved_network"]
        if isinstance(net, str) and net != IR:
            resolved[code] = net
            i_twin = by_key.get((net, code))
            if i_twin is not None:  # a row of that network exists: merge the IR row into it
                stations.loc[i_twin] = _merge_rows(stations.loc[i_twin], stations.loc[i_ir])
                drop.append(i_ir)
                locate(i_twin, row)
            else:
                stations.at[i_ir, "network"] = net
                stations.at[i_ir, "network_source"] = ISC_REGISTRY
                locate(i_ir, row)
        else:
            if not bool(row.get("ambiguous", False)) and not pd.isna(row["ir_lat"]):
                stations.at[i_ir, "network_source"] = ISC_REGISTRY_IR
            locate(i_ir, row)
            located_ir += int(not pd.isna(row["ir_lat"]))
    stations = stations.drop(index=drop)

    ir_picks = picks["network"] == IR
    to_net = ir_picks & picks["station"].isin(resolved)
    picks.loc[to_net, "network"] = picks.loc[to_net, "station"].map(resolved)
    picks.loc[to_net, "network_source"] = ISC_REGISTRY
    registry_ir = set(stations.loc[stations["network_source"] == ISC_REGISTRY_IR, "station"])
    stay = ir_picks & ~to_net & picks["station"].isin(registry_ir)
    picks.loc[stay, "network_source"] = ISC_REGISTRY_IR

    stations = stations.sort_values(["network", "station"], ignore_index=True)
    assert len(picks) == n_picks
    assert not stations.duplicated(["network", "station"]).any(), "duplicate station keys after IR decisions"
    report = {"ir_stations_resolved_registry": len(resolved), "ir_rows_merged": len(drop),
              "ir_stations_located_kept_ir": located_ir,
              "ir_picks_resolved_registry": int(to_net.sum()), "ir_picks_registry_ir": int(stay.sum())}
    logger.info("ISC registry decisions: %s", report)
    return stations, picks, report


def event_stations(picks: pd.DataFrame) -> pd.Series:
    """``NET.STA`` codes of the stations that picked each event, comma-joined and sorted."""
    codes = picks["network"].astype("string") + "." + picks["station"].astype("string")
    return (codes.groupby(picks["event_id"]).agg(lambda s: ",".join(sorted(set(s.dropna()))))
            .rename("stations"))
