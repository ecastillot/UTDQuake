"""Corrections of released v2.0 data, for v2.1 (in $UTDQUAKE_ROOT; backups in .utdquake/backups/v2.1_fix/).

1. Remove 13 events with impossible depths, and their picks: a default "maximum depth" (700.0 / 750.0 km) or a
   broken origin, in regions without deep earthquakes (a default depth also makes the epicentre unreliable).
   Real deep events (Fiji-Tonga, Sea of Okhotsk, 690-720 km) are kept. The banks keep them (banks hold
   everything downloaded).
2. Empty the magnitude of 2 uw events whose magnitude is the placeholder -5.0 (type Mh).
3. R08 (ComCat events deeper than 30 km, worldwide): continent "World" (was empty).
Network-table counts are recomputed. Each change is checked before it is made; rerunning changes nothing.
Writes <root>/.utdquake/extend/v2.1_fix.csv (one row per change).

    python fix_v2_1.py
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

from utdquake import extend as x

REMOVE = {   # utdq_net: [(event_id, depth km as found)]
    "NOA": [("smi:org.gfz-potsdam.de/geofon/noa2025iceqz", 9330.6)],
    "TUN": [("smi:ISC/evid=646693198", 693.2), ("smi:ISC/evid=646692037", 750.0)],
    "PRE": [("smi:ISC/evid=645399160", 750.0)],
    "NOU": [("smi:ISC/evid=611988905", 750.0)],
    "MDD": [("smi:ISC/evid=642662289", 747.3)],
    "JSN": [("smi:ISC/evid=646735874", 700.0), ("smi:ISC/evid=646735833", 700.0),
            ("smi:ISC/evid=644080495", 700.0), ("smi:ISC/evid=646631527", 700.0)],
    "TIR": [("smi:ISC/evid=642808167", 700.0), ("smi:ISC/evid=642636727", 700.0),
            ("smi:ISC/evid=644682086", 700.0)],
}
NO_MAGNITUDE = {"uw": ["quakeml:uw.anss.org/Event/UW/61830862", "quakeml:uw.anss.org/Event/UW/61846872"]}
CONTINENT = {"R08": "World"}

root = Path(os.environ["UTDQUAKE_ROOT"])
backups = root / ".utdquake" / "backups" / "v2.1_fix"
log = []

for net, events in REMOVE.items():
    paths = x._tables(root, net)
    ev, pk, st = (pd.read_parquet(paths[k]) for k in ("events", "picks", "stations"))
    ids = [e for e, _ in events]
    present = ev[ev["event_id"].isin(ids)]
    for eid, depth in events:
        row = present[present["event_id"] == eid]
        if row.empty:                                   # removed by an earlier run: log it from the backup
            b = backups / "events" / paths["events"].name
            old = pd.read_parquet(b) if b.exists() else pd.DataFrame(columns=["event_id"])
            row = old[old["event_id"] == eid]
            if row.empty:
                print(f"{net} {eid}: not found")
                continue
            bp = pd.read_parquet(backups / "picks" / paths["picks"].name, columns=["event_id"])
            log.append({"utdq_net": net, "event_id": eid, "change": "removed",
                        "depth_km": round(float(row["depth"].iloc[0]) / 1000.0, 1),
                        "dataset_version": row["dataset_version"].iloc[0], "picks": int((bp["event_id"] == eid).sum())})
            print(f"{net} {eid}: already removed")
            continue
        found = float(row["depth"].iloc[0]) / 1000.0
        assert abs(found - depth) < 0.1, f"{net} {eid}: depth {found} km, expected {depth}"
        log.append({"utdq_net": net, "event_id": eid, "change": "removed", "depth_km": round(found, 1),
                    "dataset_version": row["dataset_version"].iloc[0],
                    "picks": int((pk["event_id"] == eid).sum())})
    if present.empty:
        continue
    ev = ev[~ev["event_id"].isin(ids)].reset_index(drop=True)
    pk = pk[~pk["event_id"].isin(ids)].reset_index(drop=True)
    table, npath, before, after = x._network_counts(root, net, ev, pk, st)
    x._write(ev, paths["events"], backups / "events" / paths["events"].name)
    x._write(pk, paths["picks"], backups / "picks" / paths["picks"].name)
    x._write(table, npath, backups / "network" / f"network_before_{net}.parquet")
    print(f"{net}: removed {len(present)} events; network row {before} -> {after}")

for net, ids in NO_MAGNITUDE.items():
    paths = x._tables(root, net)
    ev = pd.read_parquet(paths["events"])
    rows = ev["event_id"].isin(ids) & (ev["magnitude"] <= -4.99)
    if not rows.any():
        for eid in ids:
            log.append({"utdq_net": net, "event_id": eid, "change": "magnitude -5.0 (placeholder) emptied"})
        print(f"{net}: magnitudes already emptied")
        continue
    for eid in ev.loc[rows, "event_id"]:
        log.append({"utdq_net": net, "event_id": eid, "change": "magnitude -5.0 (placeholder) emptied"})
    mag_cols = [c for c in ("magnitude", "local_magnitude", "moment_magnitude", "duration_magnitude") if c in ev]
    for c in mag_cols:
        ev.loc[rows & (ev[c] <= -4.99), c] = np.nan
    ev.loc[rows, "magnitude_type"] = pd.NA
    x._write(ev, paths["events"], backups / "events" / paths["events"].name)
    print(f"{net}: {int(rows.sum())} magnitudes emptied")

npath = root / "network" / "network.parquet"
table = pd.read_parquet(npath)
for net, continent in CONTINENT.items():
    row = table["utdq_net"] == net
    current = table.loc[row, "continent"].iloc[0]
    if pd.isna(current) or current != continent:
        log.append({"utdq_net": net, "change": f"continent {None if pd.isna(current) else current!r} -> {continent!r}"})
        table.loc[row, "continent"] = continent
        x._write(table, npath, backups / "network" / "network_before_continent.parquet")
        print(f"{net}: continent {continent}")

out = root / ".utdquake" / "extend" / "v2.1_fix.csv"
if log:
    pd.DataFrame(log).to_csv(out, index=False)                    # the full list of changes (rewritten)
print(f"{len(log)} changes; log {out}")
