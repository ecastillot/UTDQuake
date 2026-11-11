"""
Apply the ISC registry decisions (ir_decisions.parquet, from
analyze_ir_stations.py) to the seismic tables of UTDQuake_v2.

v2.0 (datasets/isc_ir_v2, copied from datasets/isc_ir): the first run copies the current stations/,
picks/, events/ and network/ to .utdquake/backups/v2.0_ir/ and every run reads its inputs from that
backup (the v1 backup_pre_ir holds the v1 tables: never read it here).
Undo: copy the backup folders back.

Per UTDQuake network with IR stations (utdquake.qc.stations.apply_ir_decisions):
stations get the registry location (confirmed) and, when resolved, the FDSN
network (merged into an existing row of that network); picks of resolved
stations get the network; the events ``stations`` column is rebuilt. The
network table's station counts, coverage bounds and ``networks`` are
recomputed. Picks already have distance, azimuth and z-scores (from the ISC
arrivals), so no pick values change except ``network``/``network_source``.

Validation (exit 1 on failure): same events and picks rows in the same order;
in picks only network/network_source differ, in events only stations; every
pick joins to exactly one station row; station keys unique.

The decisions are kept with the dataset in .utdquake/isc_registry/
ir_decisions.parquet (persistent: an extension reuses them).

Usage:
    PYTHONPATH=/groups/igonin/ecastillo/utdquake_v2ext python apply_ir_decisions.py
"""
from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

import pandas as pd

from utdquake.qc.stations import apply_ir_decisions, event_stations
from utdquake.utils.utils import get_network_summary
from utdquake.writers.migrate import _write
from utdquake.writers.schema import (PREF_EVENTS_ORDER, PREF_EVENTS_TYPES, PREF_NETWORK_ORDER,
                                     PREF_NETWORK_TYPES, PREF_PICKS_ORDER, PREF_PICKS_TYPES,
                                     PREF_STATIONS_ORDER, PREF_STATIONS_TYPES)

ROOT = Path("/groups/igonin/ecastillo/UTDQuake_v2")
BACKUP = ROOT / ".utdquake" / "backups" / "v2.0_ir"
HERE = Path(__file__).resolve().parent
DECISIONS = HERE / "ir_decisions.parquet"
REGISTRY_NAME = "isc_station_registry_2026-10-31.zip"
TABLES = ("stations", "picks", "events", "network")
COUNT_COLS = ["total_stations", "located_stations", "confirmed_stations", "calculated_stations",
              "approx_lat_min", "approx_lat_max", "approx_lon_min", "approx_lon_max"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler(HERE / "apply_ir_decisions.log", mode="w"),
                              logging.StreamHandler()])
log = logging.getLogger("apply_ir")


def backup():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for t in TABLES:
        if not (BACKUP / t).exists():
            shutil.copytree(ROOT / t, BACKUP / t)
            log.info("backed up %s", t)
    log.info("inputs read from %s", BACKUP)


def same(a: pd.DataFrame, b: pd.DataFrame, cols) -> list:
    """Columns among ``cols`` whose values differ between a and b (NA == NA)."""
    bad = []
    for c in cols:
        x, y = a[c].reset_index(drop=True), b[c].reset_index(drop=True)
        eq = (x == y).fillna(False) | (x.isna() & y.isna())
        if not bool(eq.all()):
            bad.append(c)
    return bad


def main():
    backup()
    dec = pd.read_parquet(DECISIONS)
    dec["ambiguous"] = dec["flags"].fillna("").str.split(",").apply(lambda f: "ambiguous_network" in f)
    table = pd.read_parquet(BACKUP / "network" / "network.parquet")
    rows, problems = [], []
    for net in table["utdq_net"]:
        f = f"utdq_net={net}.parquet"
        stations = pd.read_parquet(BACKUP / "stations" / f)
        picks = pd.read_parquet(BACKUP / "picks" / f)
        events = pd.read_parquet(BACKUP / "events" / f)
        d = dec[dec["utdq_net"] == net]
        if len(d):
            new_st, new_pk, report = apply_ir_decisions(stations, picks, d)
            new_ev = events.drop(columns=["stations"]).merge(event_stations(new_pk), left_on="event_id",
                                                             right_index=True, how="left")
            new_ev = new_ev[events.columns]
        else:
            new_st, new_pk, new_ev, report = stations, picks, events, {}

        # --- validation against the backup ---
        p = []
        if len(new_pk) != len(picks) or len(new_ev) != len(events):
            p.append("row counts differ")
        else:
            diff = same(picks, new_pk, [c for c in picks.columns if c not in ("network", "network_source")])
            if diff:
                p.append(f"picks columns changed: {diff}")
            diff = same(events, new_ev, [c for c in events.columns if c != "stations"])
            if diff:
                p.append(f"events columns changed: {diff}")
        if new_st.duplicated(["network", "station"]).any():
            p.append("duplicate station keys")
        joined = new_pk[["network", "station"]].merge(new_st[["network", "station"]], how="left", indicator=True)
        if len(joined) != len(new_pk) or (joined["_merge"] != "both").any():
            p.append("picks do not join to exactly one station row")
        if p:
            problems.append(f"[{net}] " + "; ".join(p))
            log.error("[%s] %s", net, p)

        if len(d):
            _write(new_st, ROOT / "stations" / f, PREF_STATIONS_TYPES, PREF_STATIONS_ORDER)
            _write(new_pk, ROOT / "picks" / f, PREF_PICKS_TYPES, PREF_PICKS_ORDER)
            _write(new_ev, ROOT / "events" / f, PREF_EVENTS_TYPES, PREF_EVENTS_ORDER)
        summary = get_network_summary(stations=new_st, events=new_ev)
        row = table["utdq_net"] == net
        before = {c: table.loc[row, c].iloc[0] for c in COUNT_COLS}
        for c in COUNT_COLS:
            table.loc[row, c] = summary[c]
        table.loc[row, "networks"] = ",".join(
            new_pk.groupby("network").size().sort_values(ascending=False, kind="stable").index)
        rows.append({"utdq_net": net, **report,
                     **{f"{c}_before": before[c] for c in COUNT_COLS[:4]},
                     **{f"{c}_after": summary[c] for c in COUNT_COLS[:4]}})
        log.info("%s: %s | stations %s -> %s, located %s -> %s, confirmed %s -> %s", net, report,
                 before["total_stations"], summary["total_stations"], before["located_stations"],
                 summary["located_stations"], before["confirmed_stations"], summary["confirmed_stations"])

    _write(table, ROOT / "network" / "network.parquet", PREF_NETWORK_TYPES, PREF_NETWORK_ORDER)
    pd.DataFrame(rows).to_csv(HERE / "apply_ir_report.csv", index=False)

    # persistent decisions, kept with the dataset
    persistent = ROOT / ".utdquake" / "isc_registry" / "ir_decisions.parquet"
    saved = BACKUP / "ir_decisions_v1.parquet"
    if not saved.exists():
        shutil.copy2(persistent, saved)
    old = pd.read_parquet(saved)
    new = dec[dec["decided_in"] == "v2.0"].assign(registry=REGISTRY_NAME)
    keep = pd.concat([old, new], ignore_index=True).drop_duplicates(["utdq_net", "station"], keep="first")
    keep.to_parquet(persistent, index=False)
    log.info("persistent decisions: %d (v1) + %d new = %d", len(old), len(new), len(keep))

    # distinct-station totals before/after (v1 and all)
    lines = []
    for label, nets in (("all", table["utdq_net"]),):
        for when, root in (("before", BACKUP), ("after", ROOT)):
            st = pd.concat([pd.read_parquet(root / "stations" / f"utdq_net={n}.parquet") for n in nets])
            ev = pd.concat([pd.read_parquet(root / "events" / f"utdq_net={n}.parquet",
                                            columns=["latitude", "longitude", "time", "p_phase_count",
                                                     "s_phase_count"]) for n in nets])
            s = get_network_summary(stations=st, events=ev, distinct_stations=True)
            lines.append({"networks": label, "when": when, "distinct_stations": s["total_stations"],
                          "located": s["located_stations"], "confirmed": s["confirmed_stations"],
                          "calculated": s["calculated_stations"]})
    totals = pd.DataFrame(lines)
    totals.to_csv(HERE / "apply_ir_totals.csv", index=False)
    log.info("distinct-station totals:\n%s", totals.to_string(index=False))

    report = pd.DataFrame(rows)
    sums = report.select_dtypes("number").sum()
    text = ["", "## Applied (`apply_ir_decisions.py`)", "",
            f"Backup of the tables before: `{BACKUP}` (undo: copy its folders back). "
            "Log: `apply_ir_decisions.log`; per network: `apply_ir_report.csv`.", "",
            f"- IR stations resolved to an FDSN network: {int(sums.get('ir_stations_resolved_registry', 0)):,} "
            f"(rows merged into an existing station of that network: {int(sums.get('ir_rows_merged', 0)):,})",
            f"- IR stations kept as IR with a registry location: {int(sums.get('ir_stations_located_kept_ir', 0)):,}",
            f"- picks re-labelled with the FDSN network: {int(sums.get('ir_picks_resolved_registry', 0)):,}; "
            f"picks of registry-only IR stations: {int(sums.get('ir_picks_registry_ir', 0)):,}",
            f"- validation: {'FAILED, see the log' if problems else 'passed'} (same events and picks; "
            "only network/network_source of picks and stations of events change; every pick joins to one station)",
            "", "Distinct stations (network, station) before and after:", "",
            "```", totals.to_string(index=False), "```", ""]
    with open(HERE / "README.md", "a") as fh:
        fh.write("\n".join(text))

    if problems:
        log.error("VALIDATION FAILED for %d networks:\n%s", len(problems), "\n".join(problems))
        sys.exit(1)
    log.info("validation passed for %d networks", len(rows))


if __name__ == "__main__":
    main()
