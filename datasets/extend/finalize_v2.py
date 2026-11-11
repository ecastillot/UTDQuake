"""Last table changes of v2.0 (after the IR step), in $UTDQUAKE_ROOT. Backups: .utdquake/backups/v2.0_finalize/.

1. R08 (ComCat events deeper than 30 km): drop the events shallower than 30 km (ComCat returned one at
   28.8 km for mindepth=30, its depth revised since) and their picks; recount the network row.
2. R11 (synthetic Delaware Basin catalog, datasets/tx_syn): copy its tables, bank, travel-time model, stats
   and figures (with R11_catalog_description.txt) from its build root, with the columns and dtypes of R10,
   picks evaluation_mode "automatic", and add its network-table row (catalog name as in tx_syn.py).

Rerunning is safe (R08: nothing left to drop; R11: copied again, row replaced).

    python finalize_v2.py /path/to/UTDQuake_txsyn
"""
import os
import shutil
import sys
from pathlib import Path

import pandas as pd

from utdquake import extend as x

root = Path(os.environ["UTDQUAKE_ROOT"])
r11_root = Path(sys.argv[1])
backups = root / ".utdquake" / "backups" / "v2.0_finalize"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tx_syn"))
import tx_syn  # noqa: E402  (MANUAL_NETWORK_INFO, UTDQ_NET)

# 1. R08
paths = x._tables(root, "R08")
ev, pk, st = (pd.read_parquet(paths[k]) for k in ("events", "picks", "stations"))
shallow = ev["depth"] < 30000
print(f"R08: {int(shallow.sum())} events shallower than 30 km: {ev.loc[shallow, 'event_id'].tolist()}")
if shallow.any():
    drop = set(ev.loc[shallow, "event_id"])
    ev, pk = ev[~shallow].reset_index(drop=True), pk[~pk["event_id"].isin(drop)].reset_index(drop=True)
    table, npath, before, after = x._network_counts(root, "R08", ev, pk, st)
    x._write(ev, paths["events"], backups / "events" / paths["events"].name)
    x._write(pk, paths["picks"], backups / "picks" / paths["picks"].name)
    x._write(table, npath, backups / "network" / "network_before_R08.parquet")
    print(f"R08 network row {before} -> {after}")

# 2. R11
net = tx_syn.UTDQ_NET
ref = x._tables(root, "R10")
for k in ("events", "picks", "stations"):
    df = pd.read_parquet(r11_root / k / f"utdq_net={net}.parquet")
    r = pd.read_parquet(ref[k])
    if k == "picks":
        df["evaluation_mode"] = "automatic"
    extra = [c for c in df.columns if c not in r.columns]
    if extra:
        print(f"R11 {k}: columns not in R10 dropped: {extra}")
    df = x._like(df, r)
    out = root / k / f"utdq_net={net}.parquet"
    x._write(df, out, backups / k / out.name)
    print(f"R11 {k}: {len(df)} rows")
for rel in (f".utdquake/travel_time/{net}.parquet", f".utdquake/stats/{net}.npz"):
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(r11_root / rel, root / rel)
for rel in (f"banks/{net}", f"figures/networks/{net}"):
    shutil.copytree(r11_root / rel, root / rel, dirs_exist_ok=True)
npath = root / "network" / "network.parquet"
table = pd.read_parquet(npath)
row = pd.read_parquet(r11_root / "network" / "network.parquet")
row = row[row["utdq_net"] == net].copy()
for c, v in tx_syn.MANUAL_NETWORK_INFO.iloc[0].items():
    row[c] = v
row = x._like(row, table)
table = pd.concat([table[table["utdq_net"] != net], row], ignore_index=True)
x._write(table, npath, backups / "network" / "network_before_R11.parquet")
print(f"R11 network row: {row[['utdq_net', 'catalog', 'catalog_type', 'events', 'p_arrivals', 's_arrivals']].to_dict('records')}")
