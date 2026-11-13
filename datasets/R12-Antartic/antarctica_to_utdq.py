"""
Ingest two Antarctic research catalogs into UTDQuake as two research networks (candidates; not published):

    R12  East Antarctica: Victoria Land / Transantarctic Mountains (2001-2003, 2012-2015), DG_ABC_quality_cat.xml:
         Ho et al., "Antarctic Upper Mantle Earthquakes Verify Intraplate Geodynamic Predictions",
         https://doi.org/10.5281/zenodo.17519077. NonLinLoc in the 3D AN1-S model with ice.
    R13  West Antarctica: Pine Island Glacier (2016), PIG_hypoDD_AB_quality.xml:
         Ho et al., "Cryospheric and Tectonic Controls on Seismicity beneath Pine Island Glacier, West Antarctica",
         https://doi.org/10.5281/zenodo.20128910. NonLinLoc (AN1-S), then hypoDD; the preferred origin is the hypoDD
         one (same origin time; it has no arrivals, the picks are those of the NonLinLoc origin).

Both: Zenodo, CC BY 4.0; Ho, L., Sanchez-Roldan, J. L., Hansen, S., Walter, J. They are far apart (about 2,500 km,
on both sides of Antarctica), so they are two networks. Stations: EarthScope (IRIS fdsnws-station),
raw/stations_channels.csv (get_stations.py). Picks with no network code (station ICE) are ER.ICE (Mount Erebus).

Each event keeps its catalog id (the QuakeML event uuid, prefixed VL_ or PIG_) and gets the region as its
event description. Depth: km below sea level (QuakeML).

Events dropped before QC: above the surface, i.e. shallower than minus the elevation of the nearest station
(R12: events piled up at -4.9 to -5.0 km, the top of the location grid).

Usage:
    python antarctica_to_utdq.py --net R12 --root ./UTDQuake_R12 [--max-events 100]
    python antarctica_to_utdq.py --net R13 --root ./UTDQuake_R13 [--from-manifests | --figures-only]
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s:%(name)s] %(message)s")
logger = logging.getLogger("antarctica_to_utdq")
logging.getLogger("utdquake.bank.utils").setLevel(logging.WARNING)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

UTDQ_NET = None  # set by --net
PICK_AGENCY = "Ho et al."
NO_NETWORK = {"ICE": "ER"}  # station -> network, for picks without a network code
COMMON = {"catalog_type": "research", "dataset_version": "v2.2",  # the next release (builds run offline)
          "country": "Antarctica", "continent": "Antarctica",
          "uploaded_by_github": "https://github.com/ecastillot", "contact_email": "castillo.280997@gmail.com"}
#: per network: (file, event id prefix, region = event description, event agency) and its network-table row
NETWORKS = {
    "R12": ((HERE / "DG_ABC_quality_cat.xml", "VL", "Victoria Land, East Antarctica",
             "Ho et al. (2025) NonLinLoc AN1-S"),
            {"catalog": "East Antarctica (Ho et al.)", "provider": "Ho et al. (2025), Zenodo",
             "provider_url": "https://zenodo.org/records/17519077", "doi": "10.5281/zenodo.17519077",
             "agency": "Victoria Land, Transantarctic Mountains: TAMSEIS (XP), TAMNNET (ZJ) and other arrays"}),
    "R13": ((HERE / "PIG_hypoDD_AB_quality.xml", "PIG", "Pine Island Glacier, West Antarctica",
             "Ho et al. (2026) hypoDD"),
            {"catalog": "West Antarctica (Ho et al.)", "provider": "Ho et al. (2026), Zenodo",
             "provider_url": "https://zenodo.org/records/20128910", "doi": "10.5281/zenodo.20128910",
             "agency": "Pine Island Glacier: PIG array (1D) and POLENET (YT)"}),
}


def network_info() -> pd.DataFrame:
    return pd.DataFrame([{"utdq_net": UTDQ_NET, **COMMON, **NETWORKS[UTDQ_NET][1]}])


def channels() -> pd.DataFrame:
    ch = pd.read_csv(RAW / "stations_channels.csv", dtype={"pick_network": str, "location": str})
    ch["pick_network"] = ch["pick_network"].fillna("")
    ch = ch[ch["network"] != "SY"]  # SY: synthetic-seismogram network, a twin of ER.ICE
    ch["start"] = pd.to_datetime(ch["start"])
    ch["end"] = pd.to_datetime(ch["end"]).fillna(pd.Timestamp("2100-01-01"))
    return ch


def stations_df(picks: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per station; only the stations of `picks` if given."""
    st = channels().groupby(["network", "station"])[["latitude", "longitude", "elevation"]].median().reset_index()
    if picks is not None:
        used = set(zip(picks["network"], picks["station"]))
        st = st[[k in used for k in zip(st["network"], st["station"])]]
    return st.reset_index(drop=True)


def instrument_types(p: pd.DataFrame) -> pd.Series:
    """Band+instrument code: from the pick's channel when it has three letters, else (channels 'Z', 'N') from
    the station's metadata at the pick time (its most common code if no epoch covers it)."""
    out = p["channel"].where(p["channel"].str.len() == 3).str[:2]
    ch = channels().assign(code=lambda d: d["channel"].str[:2])
    ch = ch[ch["code"].str[1].isin(["H", "L", "N"])]  # seismometers, not other sensors
    todo = p[out.isna()]
    for i, r in todo.iterrows():
        c = ch[(ch.network == r.network) & (ch.station == r.station)]
        now = c[(c.start <= r.pick_time) & (c.end >= r.pick_time)]
        codes = (now if len(now) else c)["code"]
        out[i] = codes.mode()[0] if len(codes) else ""
    return out


def read_source(path, prefix, region, agency):
    from obspy import read_events
    cat = read_events(str(path))
    ev_rows, pk_rows = [], []
    for ev in cat:
        o = ev.preferred_origin()
        m = ev.preferred_magnitude() or ev.magnitudes[0]
        eid = f"{prefix}_{str(ev.resource_id).split('/')[-1]}"
        q = o.quality
        ev_rows.append({
            "agency": agency, "event_id": eid, "origin_time": pd.Timestamp(o.time.datetime),
            "latitude": o.latitude, "longitude": o.longitude, "depth[km]": o.depth / 1e3,
            "latitude_error": o.latitude_errors.uncertainty, "longitude_error": o.longitude_errors.uncertainty,
            "depth_error[km]": o.depth_errors.uncertainty / 1e3 if o.depth_errors.uncertainty is not None else np.nan,
            "rms": q.standard_error if q is not None else np.nan,
            "magnitude": m.mag, "magnitude_type": m.magnitude_type, "region": region,
        })
        for p in ev.picks:
            w = p.waveform_id
            net = w.network_code or NO_NETWORK.get(w.station_code, "")
            pk_rows.append({"agency": PICK_AGENCY, "event_id": eid, "network": net, "station": w.station_code,
                            "location": None, "channel": w.channel_code or "", "phase": p.phase_hint,
                            "pick_time": pd.Timestamp(p.time.datetime)})
    ev, pk = pd.DataFrame(ev_rows), pd.DataFrame(pk_rows)
    assert ev.event_id.is_unique, f"duplicate event ids in {path.name}"
    logger.info("%s: %d events, %d picks", path.name, len(ev), len(pk))
    return ev, pk


def load(max_events: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    c, p = read_source(*NETWORKS[UTDQ_NET][0])

    st = stations_df(p)
    lat0 = np.radians(c["latitude"].values[:, None])
    dist = np.hypot((c["longitude"].values[:, None] - st["longitude"].values) * 111.2 * np.cos(lat0),
                    (c["latitude"].values[:, None] - st["latitude"].values) * 111.2)
    surface = -st["elevation"].values[dist.argmin(axis=1)] / 1000
    above = c["depth[km]"] < surface
    logger.info("above the surface (depth < -elevation of the nearest station): %s",
                c[above].groupby("region").size().to_dict())
    c = c[~above]
    if max_events is not None:
        c = c.head(max_events)
    p = p[p["event_id"].isin(c["event_id"])].copy()
    p["instrument_type"] = instrument_types(p)
    p = p.drop(columns="channel")
    key = p["network"] + "." + p["station"] + "|" + p["phase"] + "|" + p["pick_time"].astype(str)
    shared = key.duplicated(keep=False)
    if shared.any():  # a pick can belong to one event only: keep it in the event with more picks
        size = p.groupby("event_id").size()
        p = p.assign(_n=p.event_id.map(size)).sort_values("_n", ascending=False)
        logger.info("%d picks shared between events: kept in the event with more picks", int(shared.sum()))
        p = p[~key.reindex(p.index).duplicated()].drop(columns="_n")
    c = c[c["event_id"].isin(p["event_id"])]
    logger.info("%d events, %d picks (%d P, %d S); by region %s", len(c), len(p), (p.phase == "P").sum(),
                (p.phase == "S").sum(), c.groupby("region").size().to_dict())
    return c.reset_index(drop=True), p.reset_index(drop=True)


def build_catalog(events: pd.DataFrame, picks: pd.DataFrame):
    from obspy import UTCDateTime
    from obspy.core.event import Catalog, CreationInfo, Event, EventDescription, ResourceIdentifier
    from utdquake.bank.utils import get_magnitude, get_origin, get_picks

    by_event = dict(tuple(picks.groupby("event_id")))
    out = []
    for _, row in events.iterrows():
        ev_picks = get_picks(by_event[row["event_id"]])
        origin = get_origin(row[row.notna()], ev_picks)  # PIG (hypoDD) has no errors or rms: leave them out
        ev = Event(resource_id=ResourceIdentifier(id=row["event_id"], prefix="event"),
                   event_type="earthquake", picks=ev_picks, origins=[origin],
                   event_descriptions=[EventDescription(text=row["region"], type="region name")],
                   creation_info=CreationInfo(author=row["agency"], creation_time=UTCDateTime.now()))
        ev.preferred_origin_id = origin.resource_id.id
        if pd.notna(row["magnitude"]):
            mag = get_magnitude(value=row["magnitude"], mag_type=row["magnitude_type"] or "ML",
                                evaluation_mode="automatic", evaluation_status="reviewed", agency=row["agency"],
                                origin_id=origin.resource_id)
            ev.magnitudes = [mag]
            ev.preferred_magnitude_id = mag.resource_id.id
        out.append(ev)
    return Catalog(events=out)


def set_pick_agency(root: Path) -> None:
    path = root / "picks" / f"utdq_net={UTDQ_NET}.parquet"
    picks = pd.read_parquet(path)
    picks["pick_agency"] = PICK_AGENCY
    for c in picks.columns:  # same dtypes as the other networks' picks tables (str, datetime64[ns])
        if isinstance(picks[c].dtype, pd.StringDtype) or picks[c].dtype == object:
            picks[c] = picks[c].astype("str")
        elif pd.api.types.is_datetime64_any_dtype(picks[c]):
            picks[c] = picks[c].astype("datetime64[ns]")
    picks.to_parquet(path, index=False)


def figures(root: Path) -> None:
    """Stats cache and the standard figure set, into <root>/figures/networks/<net>."""
    from utdquake import generate_network_figures
    from utdquake.core.utdquake import Dataset, Network
    Dataset.networks = property(lambda self: self.local_networks)  # the local network table, not the Hub's
    Network(UTDQ_NET).compute_stats(use_cache=False)
    outdir = root / "figures" / "networks" / UTDQ_NET
    saved = generate_network_figures(UTDQ_NET, outdir=outdir, das=False)
    logger.info("%d figures in %s", len(saved), outdir)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--net", required=True, choices=sorted(NETWORKS))
    ap.add_argument("--root", required=True)
    ap.add_argument("--max-events", type=int, default=None)
    ap.add_argument("--event-chunk-size", type=int, default=250)
    ap.add_argument("--figures-only", action="store_true", help="only the stats and figures of a built root")
    ap.add_argument("--from-manifests", action="store_true",
                    help="resume a root whose bank, stations and picks are done: tables, travel times, figures")
    args = ap.parse_args()
    global UTDQ_NET
    UTDQ_NET = args.net

    os.environ["UTDQUAKE_ROOT"] = args.root
    root = Path(args.root)
    if args.figures_only:
        return figures(root)

    from utdquake.bank.bank import UTDQBank
    from utdquake.core.config import get_utdq_paths
    from utdquake.hub import check_depth_datum
    from utdquake.qc.travel_time import build_travel_time_model
    from utdquake.writers.parquet import build_manifests, publish_flat_manifests

    ebank = UTDQBank(base_path=str(get_utdq_paths(UTDQ_NET)["banks"]), path_structure="{year}/{month}/{day}",
                     name_structure="{event_id_end}", format="quakeml")

    if not args.from_manifests:
        put_bank(ebank, args)
    tables(root, build_manifests, publish_flat_manifests, build_travel_time_model, check_depth_datum)
    figures(root)


def put_bank(ebank, args):
    events, picks = load(args.max_events)
    n_pass = 0
    for i in range(0, len(events), args.event_chunk_size):
        cat = build_catalog(events.iloc[i:i + args.event_chunk_size], picks).apply_utdq_qc()
        n_pass += len(cat)
        if len(cat):
            ebank.put_events(cat)
        logger.info("events %d-%d: %d pass QC so far", i, i + args.event_chunk_size, n_pass)
    logger.info("%d events pass UTDQuake QC; bank holds %d", n_pass, len(ebank.read_index()))

    # 30-day chunks: 15 years of a sparse catalog in ~180 chunks instead of ~5,500 mostly empty days
    ebank.put_utdq_stations(stations_df(picks), das=False, calculate_d_az=True, chunk_seconds=30 * 86400)
    ebank.put_utdq_picks(chunk_size=200, apply_utdq_qc=True)


def tables(root, build_manifests, publish_flat_manifests, build_travel_time_model, check_depth_datum):
    build_manifests(utdq_nets=[UTDQ_NET], include_events=True, include_stations=True, include_picks=True,
                    include_networks=True, overwrite=True, include_manual_network_info=network_info())
    publish_flat_manifests(root=root)
    build_travel_time_model(UTDQ_NET, local_root=root, update_picks=True)
    set_pick_agency(root)

    ev = pd.read_parquet(root / "events" / f"utdq_net={UTDQ_NET}.parquet")
    sta = pd.read_parquet(root / "stations" / f"utdq_net={UTDQ_NET}.parquet")
    pk = pd.read_parquet(root / "picks" / f"utdq_net={UTDQ_NET}.parquet")
    logger.info("events without picks: %d", (~ev.event_id.isin(pk.event_id)).sum())
    logger.info("check_depth_datum: %s", check_depth_datum(ev, sta) or "OK")
    logger.info("Done: %d events, %d picks, %d stations after QC; by region %s", len(ev), len(pk), len(sta),
                ev.event_description.value_counts().to_dict() if "event_description" in ev else "?")


if __name__ == "__main__":
    main()
