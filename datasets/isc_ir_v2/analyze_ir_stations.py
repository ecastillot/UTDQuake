"""
Decide, for every station reported by ISC with the placeholder network code
``IR`` (International Registry), its FDSN network and location from the ISC
station registry. READ-ONLY on the dataset: writes only the decisions table,
a log and README.md next to this script. The step that applies the decisions
to stations/picks is separate and run after review.

Registry: UTDQuake/.utdquake/isc_registry/isc_station_registry_<date>.zip
(http://www.isc.ac.uk/registries/download/station_csv.zip). Rows: network,
station, lat, lon, elevation, channel, location, start, end, site name; one row
per station epoch (and channel for FDSN networks).

Rules, per (utdq_net, IR station), using the times of its picks:
1. IR location: registry rows (network IR, same code) whose epoch overlaps
   the pick time span. One site (all within SITE_KM) -> that location.
   Several sites -> the epoch covering most picks; flagged ``ir_moved``.
   No overlapping epoch -> nearest epoch in time, flagged ``ir_epoch_gap``.
2. FDSN network: registry rows of other networks with the same code, epoch
   overlapping the pick span, within MATCH_KM of the IR location. Exactly
   one network -> resolved (method isc_registry); several -> ambiguous,
   network stays IR.
3. Checks: distance between the registry location and the location UTDQuake
   calculated from the picks (if any); > CHECK_KM flagged ``far_from_calculated``.
   A code only in other networks (no IR rows) is resolved only if exactly
   one network matches within MATCH_KM of the calculated location.

v2.0 (datasets/isc_ir_v2): the persistent decisions of v1 (.utdquake/isc_registry/ir_decisions.parquet)
are reused for every (utdq_net, station) pair already decided; only the new pairs are decided here, with the
same registry file and rules. Copied from datasets/isc_ir (v1).

Usage:
    PYTHONPATH=/groups/igonin/ecastillo/utdquake_v2ext python analyze_ir_stations.py
"""
from __future__ import annotations

import csv
import io
import logging
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/groups/igonin/ecastillo/UTDQuake")
REGISTRY = ROOT / ".utdquake" / "isc_registry" / "isc_station_registry_2026-10-31.zip"
HERE = Path(__file__).resolve().parent
OUT = HERE / "ir_decisions.parquet"
MATCH_KM = 10.0   # same site (as the within-network twin rule)
SITE_KM = 10.0    # IR epochs closer than this are one site
CHECK_KM = 50.0   # registry vs calculated location: flag beyond this

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler(HERE / "analyze_ir_stations.log", mode="w"),
                              logging.StreamHandler()])
log = logging.getLogger("ir")


def haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def read_registry() -> pd.DataFrame:
    with zipfile.ZipFile(REGISTRY) as z:
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        text = z.read(name).decode("utf-8", errors="replace")
    rows = list(csv.reader(io.StringIO(text), skipinitialspace=True))
    bad = [r for r in rows if len(r) < 9]
    log.info("registry %s: %d rows (%d with <9 fields skipped)", REGISTRY.name, len(rows), len(bad))
    reg = pd.DataFrame([r[:9] for r in rows if len(r) >= 9],
                       columns=["network", "station", "lat", "lon", "elev", "channel", "location", "start", "end"])
    for c in ("network", "station"):
        reg[c] = reg[c].str.strip()
    for c in ("lat", "lon", "elev"):
        reg[c] = pd.to_numeric(reg[c], errors="coerce")
    for c in ("start", "end"):
        reg[c] = pd.to_datetime(reg[c].str.strip().replace("", None), utc=True, errors="coerce").dt.tz_localize(None)
    reg["end"] = reg["end"].fillna(pd.Timestamp("2100-01-01"))
    reg["start"] = reg["start"].fillna(pd.Timestamp("1900-01-01"))
    reg = reg.dropna(subset=["lat", "lon"])
    log.info("registry usable rows %d, codes %d, networks %d", len(reg), reg.station.nunique(), reg.network.nunique())
    return reg


def ir_stations() -> pd.DataFrame:
    """One row per (utdq_net, IR station): pick count and time span, calculated location."""
    table = pd.read_parquet(ROOT / "network" / "network.parquet")
    out = []
    for net, version in table[["utdq_net", "dataset_version"]].itertuples(index=False):
        st = pd.read_parquet(ROOT / "stations" / f"utdq_net={net}.parquet")
        st = st[st["network"] == "IR"]
        if st.empty:
            continue
        pk = pd.read_parquet(ROOT / "picks" / f"utdq_net={net}.parquet", columns=["network", "station", "time"])
        pk = pk[pk["network"] == "IR"]
        span = pk.groupby("station")["time"].agg(n_picks="size", pick_start="min", pick_end="max")
        span["pick_median"] = pk.groupby("station")["time"].median()
        s = st.drop_duplicates("station").set_index("station")
        df = span.join(s[["calculated_latitude", "calculated_longitude", "calculated"]], how="outer")
        df["utdq_net"], df["dataset_version"] = net, version
        out.append(df.reset_index().rename(columns={"index": "station"}))
        log.info("%s: %d IR stations, %d IR picks", net, len(df), len(pk))
    df = pd.concat(out, ignore_index=True)
    df["n_picks"] = df["n_picks"].fillna(0).astype(int)
    return df


def decide(row, reg_ir: dict, reg_real: dict) -> dict:
    code, t0, t1, tm = row.station, row.pick_start, row.pick_end, row.pick_median
    clat, clon = row.calculated_latitude, row.calculated_longitude
    d = {"ir_lat": np.nan, "ir_lon": np.nan, "ir_elev": np.nan, "ir_epoch_start": pd.NaT, "ir_epoch_end": pd.NaT,
         "resolved_network": "IR", "method": "unresolved", "n_candidate_networks": 0, "flags": [],
         "candidates": ""}
    ir = reg_ir.get(code)
    have_time = pd.notna(t0)
    if ir is not None:
        e = ir[(ir.start <= t1) & (ir.end >= t0)] if have_time else ir
        if e.empty:
            # nearest epoch in time
            gap = np.minimum((ir.start - tm).abs(), (ir.end - tm).abs()) if have_time else ir.start
            e = ir.loc[[gap.idxmin()]]
            d["flags"].append("ir_epoch_gap")
        sites = haversine_km(e.lat.values[:, None], e.lon.values[:, None], e.lat.values[None, :], e.lon.values[None, :])
        if sites.max() > SITE_KM:
            d["flags"].append("ir_moved")
            cover = (e.start <= tm) & (e.end >= tm) if have_time else pd.Series(True, index=e.index)
            e = e[cover] if cover.any() else e
            e = e.loc[[e.end.idxmax()]]
        best = e.iloc[0]
        d.update(ir_lat=best.lat, ir_lon=best.lon, ir_elev=best.elev, ir_epoch_start=best.start, ir_epoch_end=best.end,
                 method="isc_registry_ir")
        ref_lat, ref_lon = best.lat, best.lon
    elif pd.notna(clat):
        ref_lat, ref_lon = clat, clon
        d["flags"].append("no_ir_entry")
    else:
        d["flags"].append("not_in_registry" if code not in reg_real else "no_ir_entry_no_location")
        d["flags"] = ",".join(d["flags"])
        return d

    real = reg_real.get(code)
    if real is not None:
        r = real[(real.start <= t1) & (real.end >= t0)] if have_time else real
        r = r.assign(km=haversine_km(ref_lat, ref_lon, r.lat.values, r.lon.values))
        r = r[r.km <= MATCH_KM]
        nets = sorted(r.network.unique())
        d["n_candidate_networks"] = len(nets)
        d["candidates"] = ",".join(f"{n}:{r[r.network == n].km.min():.1f}km" for n in nets)
        if len(nets) == 1:
            d["resolved_network"] = nets[0]
            d["method"] = "isc_registry" if ir is not None else "isc_registry_from_calculated"
            if ir is None:  # location from the matched network
                m = r[r.network == nets[0]].iloc[0]
                d.update(ir_lat=m.lat, ir_lon=m.lon, ir_elev=m.elev)
        elif len(nets) > 1:
            d["flags"].append("ambiguous_network")
    if pd.notna(clat) and pd.notna(d["ir_lat"]):
        d["km_registry_vs_calculated"] = float(haversine_km(clat, clon, d["ir_lat"], d["ir_lon"]))
        if d["km_registry_vs_calculated"] > CHECK_KM:
            d["flags"].append("far_from_calculated")
    d["flags"] = ",".join(d["flags"])
    return d


def has_flag(df: pd.DataFrame, flag: str) -> pd.Series:
    """Rows whose comma-separated ``flags`` contain exactly ``flag``."""
    return df["flags"].fillna("").str.split(",").apply(lambda f: flag in f)


def readme(df: pd.DataFrame) -> str:
    def count(mask):
        return int(mask.sum())
    v1 = df[df.dataset_version == "v1"]
    lines = ["# ISC `IR` stations: network and location from the ISC station registry", "",
             "Generated by `analyze_ir_stations.py` (read-only on the dataset). Log: `analyze_ir_stations.log`. "
             "Decisions: `ir_decisions.parquet` / `ir_decisions.csv`.", "",
             f"Registry file: `{REGISTRY}` (ISC `station_csv.zip`, downloaded 2026-10-31; sha256 in `SHA256SUMS`).",
             f"Rules: same site = within {MATCH_KM:g} km; epochs must overlap the station's pick time span; "
             f"registry vs calculated location checked at {CHECK_KM:g} km. See the module docstring.", "",
             "## Why", "",
             "ISC reports picks of stations it only knows from its International Registry with the network code "
             "`IR`. ISC has no FDSN station service, so these stations had no confirmed location (0 of them) and "
             "their real FDSN network was unknown unless a same-code station of another network was found within "
             "10 km in the same UTDQuake network. The registry (downloadable) gives every IR station's location and "
             "epochs, and lists FDSN networks too, so both can be decided from ISC's own data.", "",
             "## Results (IR pairs in the v2.0 tables; decided in v1 in brackets)", "",
             "| | (utdq_net, station) pairs | IR picks |", "|---|---|---|"]
    for label, mask in [("IR stations", df.station.notna()),
                        ("location from the registry", df.ir_lat.notna()),
                        ("resolved to one FDSN network", df.resolved_network != "IR"),
                        ("kept IR: registered only as IR", (df.resolved_network == "IR") & df.ir_lat.notna()
                         & ~has_flag(df, "ambiguous_network")),
                        ("kept IR: ambiguous (2+ networks at the site)", has_flag(df, "ambiguous_network")),
                        ("not in the registry / no location", df.ir_lat.isna())]:
        lines.append(f"| {label} | {count(mask):,} ({count(mask[v1.index]):,}) | "
                     f"{int(df.loc[mask, 'n_picks'].sum()):,} ({int(v1.loc[mask[v1.index], 'n_picks'].sum()):,}) |")
    lines += ["", "## Flags (to review before applying)", "", "| flag | pairs | meaning |", "|---|---|---|"]
    meaning = {"ir_moved": "IR epochs at sites > 10 km apart; the epoch covering the median pick time is used",
               "ir_epoch_gap": "no IR epoch overlaps the picks; the nearest epoch in time is used",
               "far_from_calculated": f"registry location > {CHECK_KM:g} km from the location calculated from picks",
               "ambiguous_network": "2+ FDSN networks with this code at the site; network stays IR",
               "no_ir_entry": "code only under FDSN networks; matched near the calculated location",
               "no_ir_entry_no_location": "code only under FDSN networks and no calculated location: not decided",
               "not_in_registry": "code not in the registry"}
    for flag, text in meaning.items():
        lines.append(f"| `{flag}` | {count(has_flag(df, flag)):,} | {text} |")
    lines += ["", "## Resolved networks (top 20, pairs)", "", "```",
              df[df.resolved_network != "IR"].resolved_network.value_counts().head(20).to_string(), "```", "",
              "## Applying the decisions", "",
              "`apply_ir_decisions.py` (its results are appended below when it runs). It applies the decisions: set `network`/location of these stations in the stations tables "
              "(`network_source = isc_registry`, `confirmed` from the registry), the `network` of their picks, "
              "recompute distance/azimuth and travel-time z-scores of the picks that gain a location, then "
              "recompute counts, validate (no pick/event rows change) and regenerate figures and totals. "
              "The decisions are kept as a persistent registry so a later extension (v2) reuses them and only "
              "decides new stations.", ""]
    return "\n".join(lines)


PERSISTENT = ROOT / ".utdquake" / "isc_registry" / "ir_decisions.parquet"


def main():
    reg = read_registry()
    reg_ir = {k: g for k, g in reg[reg.network == "IR"].groupby("station")}
    reg_real = {k: g for k, g in reg[reg.network != "IR"].groupby("station")}
    df = ir_stations()
    log.info("IR (utdq_net, station) pairs: %d, codes %d", len(df), df.station.nunique())
    old = pd.read_parquet(PERSISTENT)
    known = df.set_index(["utdq_net", "station"]).index.isin(old.set_index(["utdq_net", "station"]).index)
    log.info("pairs decided in v1 (reused): %d; new pairs decided now: %d", known.sum(), (~known).sum())
    new = df[~known].reset_index(drop=True)
    decisions = pd.DataFrame([decide(r, reg_ir, reg_real) for r in new.itertuples(index=False)], index=new.index)
    new = pd.concat([new, decisions], axis=1)
    new["km_registry_vs_calculated"] = new.get("km_registry_vs_calculated")
    new["decided_in"] = "v2.0"
    reused = old.merge(df.loc[known, ["utdq_net", "station"]], on=["utdq_net", "station"])
    reused["decided_in"] = reused.get("decided_in", "v1")
    df = pd.concat([reused, new], ignore_index=True)
    df["dataset_version"] = df["decided_in"]
    df.to_parquet(OUT, index=False)
    df.to_csv(OUT.with_suffix(".csv"), index=False)
    (HERE / "README.md").write_text(readme(df))
    log.info("method counts:\n%s", df.method.value_counts().to_string())
    log.info("flags:\n%s", df['flags'].value_counts().head(20).to_string())
    log.info("km registry vs calculated (where both):\n%s", df.km_registry_vs_calculated.describe().to_string())
    log.info("done: %s, README.md", OUT)


if __name__ == "__main__":
    main()
