"""
Bring the pick tables of the networks added after the 82 originals
(5B, ISOR, SYN_QTM, comcat_deep30, CM) to the documented 32-column schema.

- drop the 13 obsplus pick columns (onset, polarity, event_time, ...) that
  sanitize_dataframe used to create as empty columns (all 100% null),
- fill pick_agency like the original networks: FDSN network code from seed_id,
- compute travel_time_zscore where it is missing/empty (CM, 5B, SYN_QTM)
  with build_travel_time_model (also writes .utdquake/travel_time/{net}.parquet),
- cast to the exact Arrow schema of the original networks (timestamp[ns], ...).

Works on a test root first. Run with --promote to copy the result into the
real UTDQuake root (originals backed up to picks_bck/schemafix_20260927/).
"""
import argparse
import shutil
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from utdquake.qc.travel_time import build_travel_time_model

REAL = Path("/groups/igonin/ecastillo/UTDQuake")
TEST = Path("/groups/igonin/ecastillo/UTDQuake_schemafix")
NETS = ["5B", "ISOR", "SYN_QTM", "comcat_deep30", "CM"]
NEED_ZSCORE = ["CM", "5B", "SYN_QTM"]
REF = REAL / "picks/network=tx.parquet"   # one of the 82 original networks
BACKUP = REAL / "picks_bck/schemafix_20260927"

ref_schema = pq.read_schema(REF).remove_metadata()
STD = ref_schema.names


def picks_path(root, net):
    return root / f"picks/network={net}.parquet"


def to_standard(df):
    df = df[[c for c in df.columns if c in STD]].copy()
    for c in STD:
        if c not in df.columns:
            df[c] = pd.NA
    fdsn = df["seed_id"].str.split(".").str[0]
    df["pick_agency"] = df["pick_agency"].fillna(fdsn)
    return df[STD]


def write_standard(df, path):
    df = df.sort_values("time", kind="stable", ignore_index=True)
    table = pa.Table.from_pandas(df, preserve_index=False).cast(ref_schema)
    pq.write_table(table, path)


def build():
    (TEST / "picks").mkdir(parents=True, exist_ok=True)
    for net in NETS:
        df = to_standard(pd.read_parquet(picks_path(REAL, net)))
        write_standard(df, picks_path(TEST, net))
        print(f"{net}: standardized {len(df)} picks")

    for net in NEED_ZSCORE:
        build_travel_time_model(net, local_root=TEST)   # rewrites TEST picks
        df = to_standard(pd.read_parquet(picks_path(TEST, net)))
        write_standard(df, picks_path(TEST, net))
        print(f"{net}: travel_time_zscore filled "
              f"{df.travel_time_zscore.notna().mean():.3f}")


def validate():
    ok = True
    for net in NETS:
        old = pd.read_parquet(picks_path(REAL, net))
        new = pd.read_parquet(picks_path(TEST, net))
        schema_ok = pq.read_schema(picks_path(TEST, net)).remove_metadata().equals(ref_schema)
        rows_ok = len(old) == len(new)
        # every value except the two filled columns must be unchanged
        keep = [c for c in STD if c in old.columns and c not in ("pick_agency", "travel_time_zscore")]
        a = old[keep].sort_values("resource_id", ignore_index=True)
        b = new[keep].sort_values("resource_id", ignore_index=True)
        a[a.select_dtypes("datetime").columns] = a.select_dtypes("datetime").astype("datetime64[ns]")
        values_ok = a.astype(str).equals(b.astype(str))
        agency_ok = new.pick_agency.notna().all() and (
            new.pick_agency == new.seed_id.str.split(".").str[0]).all()
        z = new.travel_time_zscore.notna().mean()
        if "travel_time_zscore" in old and old.travel_time_zscore.notna().any():
            z_ok = old.set_index("resource_id").travel_time_zscore.sort_index().equals(
                new.set_index("resource_id").travel_time_zscore.sort_index())
        else:
            z_ok = z > 0.9
        print(f"{net}: schema={schema_ok} rows={rows_ok} values={values_ok} "
              f"pick_agency={agency_ok} {sorted(new.pick_agency.unique())[:5]} "
              f"zscore={z_ok} ({z:.3f} filled)")
        ok &= schema_ok and rows_ok and values_ok and agency_ok and z_ok
    return ok


def promote():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for net in NETS:
        shutil.copy2(picks_path(REAL, net), BACKUP / picks_path(REAL, net).name)
        shutil.copy2(picks_path(TEST, net), picks_path(REAL, net))
    for net in NEED_ZSCORE:
        src = TEST / f".utdquake/travel_time/{net}.parquet"
        shutil.copy2(src, REAL / ".utdquake/travel_time" / src.name)
    print(f"Promoted {NETS}; originals in {BACKUP}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--promote", action="store_true")
    args = p.parse_args()
    if args.promote:
        if not validate():
            raise SystemExit("Validation failed; not promoting.")
        promote()
    else:
        build()
        print("ALL OK" if validate() else "VALIDATION FAILED")
