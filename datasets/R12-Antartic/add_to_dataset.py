"""Add R12 (East Antarctica) and R13 (West Antarctica) to the UTDQuake dataset in $UTDQUAKE_ROOT (release v2.2).

From each build root (datasets/R12-Antartic/UTDQuake_<net>, made by run_build.sh): the events, picks and stations
tables (columns and dtypes of R10), the bank, the travel-time model, the stats cache, the figures, and the
network-table row. Only new files are written, plus the network table (backup first, in
.utdquake/backups/v2.2_add/). Refuses to overwrite a network already in the dataset unless --replace.

    UTDQUAKE_ROOT=/groups/igonin/ecastillo/UTDQuake python add_to_dataset.py [--replace]
"""
import argparse
import os
import shutil
from pathlib import Path

import pandas as pd

from utdquake import extend as x

HERE = Path(__file__).resolve().parent
NETS = ("R12", "R13")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", action="store_true", help="replace the networks if they are already there")
    args = ap.parse_args()
    root = Path(os.environ["UTDQUAKE_ROOT"])
    backups = root / ".utdquake" / "backups" / "v2.2_add"
    npath = root / "network" / "network.parquet"
    table = pd.read_parquet(npath)
    there = sorted(set(NETS) & set(table["utdq_net"].astype(str)))
    if there and not args.replace:
        raise SystemExit(f"{there} already in {npath}: nothing done (use --replace)")
    ref = x._tables(root, "R10")
    rows = []
    for net in NETS:
        src = HERE / f"UTDQuake_{net}"
        for k in ("events", "picks", "stations"):
            df = x._like(pd.read_parquet(src / k / f"utdq_net={net}.parquet"), pd.read_parquet(ref[k]))
            out = root / k / f"utdq_net={net}.parquet"
            x._write(df, out, backups / k / out.name)
            print(f"{net} {k}: {len(df)} rows")
        for rel in (f".utdquake/travel_time/{net}.parquet", f".utdquake/stats/{net}.npz"):
            shutil.copy2(src / rel, root / rel)
        for rel in (f"banks/{net}", f"figures/networks/{net}"):
            shutil.copytree(src / rel, root / rel, dirs_exist_ok=True)
        row = pd.read_parquet(src / "network" / "network.parquet")
        rows.append(row[row["utdq_net"] == net])
    new = x._like(pd.concat(rows, ignore_index=True), table)
    table = pd.concat([table[~table["utdq_net"].isin(NETS)], new], ignore_index=True)
    x._write(table, npath, backups / "network" / "network_before_R12_R13.parquet")
    print(f"network table: {len(table)} networks")
    print(new[["utdq_net", "catalog", "catalog_type", "dataset_version", "events", "p_arrivals", "s_arrivals",
               "total_stations"]].to_string())


if __name__ == "__main__":
    main()
