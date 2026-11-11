"""Checks of the merged UTDQuake tables against the pre-merge backups (<root>/.utdquake/backups/v2.0_merge).

    python validate_merge.py ROOT VERSION NET [NET ...]

For every network: no duplicated events or stations, picks <-> events consistent, every v1 event still there
(rebuilt for REPLACE networks), v1 rows keep their label, the network table counts match, dtypes as before.
Writes <root>/.utdquake/extend/<version>/merge_summary.csv and exits 1 if a check fails.
"""
import sys
from pathlib import Path
import pandas as pd
from utdquake import extend as x

root, version, nets = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
label = x.version_label(version)
backups = root / ".utdquake" / "backups" / f"{version}_merge"
table = pd.read_parquet(root / "network" / "network.parquet")
ok, rows = True, []


def check(cond, msg):
    global ok
    if not cond:
        print("FAIL " + msg)
    ok &= bool(cond)


for n in nets:
    ev = pd.read_parquet(root / "events" / f"utdq_net={n}.parquet")
    pk = pd.read_parquet(root / "picks" / f"utdq_net={n}.parquet")
    st = pd.read_parquet(root / "stations" / f"utdq_net={n}.parquet")
    b = {k: backups / k / f"utdq_net={n}.parquet" for k in ("events", "picks", "stations")}
    old = {k: pd.read_parquet(p) if p.exists() else None for k, p in b.items()}
    check(not ev.event_id.duplicated().any(), f"{n} duplicated events")
    check(pk.event_id.isin(ev.event_id).all(), f"{n} picks of missing events")
    nopk = ~ev.event_id.isin(pk.event_id)  # some v1 events have no picks (counts only): only new ones fail
    if old["events"] is not None and n not in x.REPLACE:
        nopk &= ~ev.event_id.isin(old["events"].event_id)
    check(not nopk.any(), f"{n} new events without picks: {nopk.sum()}")
    check(not st.duplicated(["network", "station"]).any(), f"{n} duplicated stations")
    check(not pk.duplicated(["event_id", "pick_id"]).any() if "pick_id" in pk else True, f"{n} duplicated picks")
    v = ev.dataset_version.value_counts().to_dict()
    o = old["events"]
    if o is not None:
        check(o.event_id.isin(ev.event_id).all(),
              f"{n} v1 events missing: {(~o.event_id.isin(ev.event_id)).sum()}")
        if n in x.REPLACE:
            check(set(v) == {label}, f"{n} replace: versions {v}")
        else:
            kept = ev[ev.event_id.isin(o.event_id)]
            check((kept.dataset_version.values == o.set_index("event_id").loc[kept.event_id, "dataset_version"].values).all(),
                  f"{n} v1 labels changed")
            check(len(pk) >= len(old["picks"]), f"{n} fewer picks than before")
            check(len(st) >= len(old["stations"]), f"{n} fewer stations than before")
        for k, new in (("events", ev), ("picks", pk), ("stations", st)):
            bad = {c: (str(new[c].dtype), str(old[k][c].dtype)) for c in old[k].columns
                   if c in new and str(new[c].dtype) != str(old[k][c].dtype)}
            check(not bad and list(new.columns) == list(old[k].columns), f"{n} {k} columns/dtypes {bad}")
    r = table[table.utdq_net == n]
    check(len(r) == 1, f"{n} network table rows {len(r)}")
    if len(r) == 1:
        check(int(r.iloc[0].events) == len(ev), f"{n} network table events {r.iloc[0].events} != {len(ev)}")
    s = pk.phase.astype(str).str.upper().str.startswith("S").sum()
    rows.append({"utdq_net": n, "events_before": 0 if o is None else len(o), "events": len(ev),
                 "v1": v.get("v1", 0), label: v.get(label, 0), "picks_before": 0 if o is None else len(old["picks"]),
                 "picks": len(pk), "P": len(pk) - s, "S": s,
                 "stations_before": 0 if o is None else len(old["stations"]), "stations": len(st)})

out = pd.DataFrame(rows)
out.loc[len(out)] = ["TOTAL"] + out.drop(columns="utdq_net").sum().tolist()
path = root / ".utdquake" / "extend" / version / "merge_summary.csv"
out.to_csv(path, index=False)
print(out.to_string(index=False))
print(f"summary: {path}")
print("ALL OK" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
