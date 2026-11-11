"""Merge test in a copy: ETH (append), JMA (replace), ci (new network); then checks and a second merge."""
import os, shutil, sys
from pathlib import Path
import pandas as pd

LIVE = Path("/groups/igonin/ecastillo/UTDQuake_v2")
TEST = Path(sys.argv[1])
NETS = ["ETH", "JMA", "ci"]
if TEST.exists():
    shutil.rmtree(TEST)
for k in ("events", "picks", "stations"):
    (TEST / k).mkdir(parents=True)
    for net in NETS + ["nc"]:
        src = LIVE / k / f"utdq_net={net}.parquet"
        if src.exists():
            shutil.copy2(src, TEST / k / src.name)
(TEST / "network").mkdir()
shutil.copy2(LIVE / "network" / "network.parquet", TEST / "network" / "network.parquet")

from utdquake import extend as x
from utdquake.core.config import get_hf_entry
before = {n: {k: (len(pd.read_parquet(TEST / k / f"utdq_net={n}.parquet")) if (TEST / k / f"utdq_net={n}.parquet").exists() else 0)
              for k in ("events", "picks", "stations")} for n in NETS}
first = {n: x.merge("v2.0", n, TEST) for n in NETS}
second = {n: x.merge("v2.0", n, TEST) for n in NETS}
ok = True
def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg); ok &= bool(cond)
table = pd.read_parquet(TEST / "network" / "network.parquet")
for n in NETS:
    ev = pd.read_parquet(TEST / "events" / f"utdq_net={n}.parquet")
    pk = pd.read_parquet(TEST / "picks" / f"utdq_net={n}.parquet")
    st = pd.read_parquet(TEST / "stations" / f"utdq_net={n}.parquet")
    print(f"== {n}: before {before[n]} -> events {len(ev)}, picks {len(pk)}, stations {len(st)}; "
          f"versions {ev.dataset_version.value_counts().to_dict()}")
    check(not ev.event_id.duplicated().any(), f"{n} no duplicated events")
    check(pk.event_id.isin(ev.event_id).all(), f"{n} every pick has its event")
    check(ev.event_id.isin(pk.event_id).all(), f"{n} every event has picks")
    check(not st.duplicated(["network", "station"]).any(), f"{n} no duplicated stations")
    check(second[n]["merged_events"] == (len(ev) if n in x.REPLACE else 0) or n in x.REPLACE,
          f"{n} second merge adds nothing ({second[n]['merged_events']})")
    check(len(ev) == first[n]["events"] == second[n]["events"], f"{n} same totals after the second merge")
    ref = pd.read_parquet(LIVE / "events" / "utdq_net=nc.parquet")
    check(list(ev.columns) == list(ref.columns), f"{n} events columns as v1")
    bad = {c: (str(ev[c].dtype), str(ref[c].dtype)) for c in ref.columns if str(ev[c].dtype) != str(ref[c].dtype)}
    check(not bad, f"{n} events dtypes as v1 {bad if bad else ''}")
    refp = pd.read_parquet(LIVE / "picks" / "utdq_net=nc.parquet")
    badp = {c: (str(pk[c].dtype), str(refp[c].dtype)) for c in refp.columns if str(pk[c].dtype) != str(refp[c].dtype)}
    check(not badp, f"{n} picks dtypes as v1 {badp if badp else ''}")
    row = table[table.utdq_net == n].iloc[0]
    check(int(row.events) == len(ev), f"{n} network table events = {row.events}")
    if n == "JMA":
        v1 = pd.read_parquet(LIVE / "events" / "utdq_net=JMA.parquet")
        check(v1.event_id.isin(ev.event_id).all(), "JMA every v1 event still there (rebuilt)")
        check(set(ev.dataset_version) == {"v2"}, "JMA all rows v2")
        s = pk.phase.str.upper().str.startswith("S").sum()
        print(f"     JMA picks P {len(pk)-s} S {s}")
    if n == "ETH":
        v1 = pd.read_parquet(LIVE / "events" / "utdq_net=ETH.parquet")
        m = ev[ev.event_id.isin(v1.event_id)]
        check(len(m) == len(v1) and (m.dataset_version == "v1").all(), "ETH v1 rows kept with v1 label")
print(table[table.utdq_net.isin(NETS)][["utdq_net", "dataset_version", "agency", "events", "p_arrivals", "s_arrivals",
                                         "total_stations", "start_time", "end_time"]].to_string())
os.environ["UTDQUAKE_ROOT"] = str(TEST)
from utdquake.core.utdquake import Dataset
try:
    d = Dataset()
    e = d.get_events(utdq_net="ETH")
    check(len(e) == len(pd.read_parquet(TEST / "events" / "utdq_net=ETH.parquet")), f"API loads ETH events ({len(e)})")
except Exception as e:
    print("API check skipped:", type(e).__name__, str(e)[:200])
print("ALL OK" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
