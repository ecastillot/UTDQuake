"""
Ingest the DETECT enhanced catalog (Irpinia, Southern Italy, FDSN network ZK, Sep 2021 - Jul 2022) into
UTDQuake as research network R10 (catalog "DETECT", dataset_version v2).

Source: Scotto di Uccio, F. et al. (2025). Enhanced seismic catalog for the seismicity observed during
the DETECT experiment, Southern Italy. Zenodo. https://doi.org/10.5281/zenodo.15372023 (CC BY 4.0).
Network paper: Scotto di Uccio et al. (2026), ESSD 18, 7751, https://doi.org/10.5194/essd-18-7751-2026;
waveforms/stations: GEOFON, network ZK (https://doi.org/10.14470/MX7576871994). Detection: EQTransformer,
then template matching (EQCorrscan); picks automatic.

Inputs (raw/, from Zenodo and the GEOFON station service):
    catalog_location_magnitude_DETECT.txt   TIME,LAT,LON,DEP,ML,ML_std (one row per event)
    P_pick_merged.txt, S_pick_merged.txt     one row per event (same order), one column per station
    zk_channels.txt                          fdsnws-station level=channel text for ZK

The files have no event id: events are matched to picks by row, and get the id DETECT_<row> (1-based).
Depth: km, taken as below sea level (stations at 0.19-1.17 km a.s.l.).

Events dropped before QC (see notes.md):
    - no location (38);
    - origin time on a whole second (ms 000/001/999; 637): their picks are ~0.75 s late on average
      against the other events' (P and S, same distance fit), i.e. the origin times are rounded or
      shifted; as LASSO's GENIE origins, they would bias the travel times;
    - above the surface: depth shallower than minus the elevation of the nearest station (141, piled
      up at -2.0 km, the top of a location grid).

instrument_type: band+instrument code from GEOFON of the sensor at the pick time (DH geophones, CH 1 Hz,
HH broadband); S0617 and S1003 changed sensor (the picks do not give the channel).

Usage:
    python detect_to_utdq.py --root ./UTDQuake_DETECT [--max-events 100]
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s:%(name)s] %(message)s")
logger = logging.getLogger("detect_to_utdq")
logging.getLogger("utdquake.bank.utils").setLevel(logging.WARNING)

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

UTDQ_NET = "R10"
FDSN_NETWORK = "ZK"
EVENT_AGENCY = "DETECT"
PICK_AGENCY = "EQTransformer+EQCorrscan"

MANUAL_NETWORK_INFO = pd.DataFrame({
    "utdq_net": [UTDQ_NET],
    "catalog": ["DETECT"],
    "catalog_type": ["research"],
    "dataset_version": ["v2"],
    "provider": ["Scotto di Uccio et al. (2025), Zenodo"],
    "provider_url": ["https://zenodo.org/records/15372023"],
    "country": ["Italy"],
    "agency": ["DETECT dense arrays, Irpinia fault system (FDSN ZK, GFZ/Univ. Naples Federico II)"],
    "continent": ["Europe"],
    "uploaded_by_github": ["https://github.com/ecastillot"],
    "contact_email": ["castillo.280997@gmail.com"],
    "doi": ["10.5281/zenodo.15372023"],
})


def channels() -> pd.DataFrame:
    ch = pd.read_csv(RAW / "zk_channels.txt", sep="|")
    ch.columns = [c.strip("#").strip() for c in ch.columns]
    return ch


def stations_df() -> pd.DataFrame:
    ch = channels()
    st = ch.sort_values("StartTime").groupby("Station").last()  # coordinates are the same in every epoch
    return pd.DataFrame({"network": FDSN_NETWORK, "station": st.index,
                         "latitude": st["Latitude"], "longitude": st["Longitude"],
                         "elevation": st["Elevation"]}).reset_index(drop=True)


def instrument_types(p: pd.DataFrame) -> pd.Series:
    """Band+instrument code (DH, CH, HH) of the sensor a station had at the pick time: two stations
    changed sensor (S0617 DH -> HH -> DH, S1003 DH -> CH). Picks outside every epoch get the station's
    most common code."""
    ch = channels()
    ep = ch.assign(code=ch["Channel"].str[:2], start=pd.to_datetime(ch["StartTime"]),
                   end=pd.to_datetime(ch["EndTime"]))[["Station", "code", "start", "end"]].drop_duplicates()
    m = p[["station", "pick_time"]].reset_index().merge(ep, left_on="station", right_on="Station")
    m = m[(m["pick_time"] >= m["start"]) & (m["pick_time"] <= m["end"])].drop_duplicates("index")
    out = pd.Series(m["code"].values, index=m["index"]).reindex(p.index)
    common = ep.groupby("Station")["code"].agg(lambda s: s.mode()[0])
    return out.fillna(p["station"].map(common))


def load(max_events: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    c = pd.read_csv(RAW / "catalog_location_magnitude_DETECT.txt")
    c["event_id"] = [f"DETECT_{i + 1:04d}" for i in range(len(c))]
    c["time"] = pd.to_datetime(c["TIME"])
    n0 = len(c)

    located = c[["LAT", "LON", "DEP"]].notna().all(axis=1)
    whole = (c["time"].dt.microsecond // 1000).isin([0, 1, 999])
    st = stations_df()
    dist = np.hypot((c["LON"].values[:, None] - st["longitude"].values) * 111.2 * np.cos(np.radians(40.75)),
                    (c["LAT"].values[:, None] - st["latitude"].values) * 111.2)
    surface = -st["elevation"].values[np.nan_to_num(dist, nan=1e9).argmin(axis=1)] / 1000
    above = located & (c["DEP"] < surface)
    keep = located & ~whole & ~above
    logger.info("%d events: %d without location, %d with whole-second origin times, %d above the surface"
                " (of the rest) -> %d kept", n0, (~located).sum(), (located & whole).sum(),
                (located & ~whole & above).sum(), keep.sum())
    c = c[keep]
    if max_events is not None:
        c = c.iloc[:max_events]

    picks = []
    for phase in ("P", "S"):
        t = pd.read_csv(RAW / f"{phase}_pick_merged.txt")
        t["event_id"] = [f"DETECT_{i + 1:04d}" for i in range(len(t))]
        m = t.melt("event_id", var_name="station", value_name="pick_time")
        m = m[(m["pick_time"] != "NaT") & m["event_id"].isin(c["event_id"])]
        m["phase"] = phase
        picks.append(m)
    p = pd.concat(picks, ignore_index=True)
    p["pick_time"] = pd.to_datetime(p["pick_time"])
    p["instrument_type"] = instrument_types(p)
    p = pd.DataFrame({
        "agency": PICK_AGENCY,
        "event_id": p["event_id"],
        "network": FDSN_NETWORK,
        "station": p["station"],
        "location": None,
        "instrument_type": p["instrument_type"],
        "phase": p["phase"],
        "pick_time": p["pick_time"],
    })
    p, c = shared_picks(p, c)
    c = c[c["event_id"].isin(p["event_id"])]
    events = pd.DataFrame({
        "agency": EVENT_AGENCY,
        "event_id": c["event_id"],
        "origin_time": c["time"],
        "latitude": c["LAT"],
        "longitude": c["LON"],
        "depth[km]": c["DEP"],
        "magnitude": c["ML"],
        "magnitude_error": c["ML_std"],
    }).reset_index(drop=True)
    logger.info("%d events, %d picks (%d P, %d S)", len(events), len(p), (p.phase == "P").sum(),
                (p.phase == "S").sum())
    return events, p.reset_index(drop=True)


def shared_picks(p: pd.DataFrame, c: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A pick (station, phase, time) can belong to one event only. Pairs of events that share picks
    (13 in the catalog): origins < 1 s apart sharing at least half of the smaller event's picks are the
    same event listed twice (8; the one with fewer picks is dropped); otherwise the shared picks are
    removed from the event with fewer picks (5)."""
    key = p["station"] + "|" + p["phase"] + "|" + p["pick_time"].astype(str)
    sets = key.groupby(p["event_id"]).apply(set)
    pairs = key[key.duplicated(keep=False)].groupby(key).apply(lambda s: tuple(sorted(set(p.loc[s.index, "event_id"]))))
    t = c.set_index("event_id")["time"]
    drop_events, drop_picks = set(), set()
    for pair in pairs.unique():
        small, big = sorted(pair, key=lambda e: (len(sets[e]), e))[:2]
        shared = sets[small] & sets[big]
        if abs((t[small] - t[big]).total_seconds()) < 1 and len(shared) >= 0.5 * len(sets[small]):
            drop_events.add(small)
        else:
            drop_picks |= {(small, k) for k in shared}
    keep = ~p["event_id"].isin(drop_events) & ~pd.Series(list(zip(p["event_id"], key)), index=p.index).isin(drop_picks)
    logger.info("events sharing picks: %d duplicates dropped, %d shared picks removed from %d events",
                len(drop_events), len(drop_picks), len({e for e, _ in drop_picks}))
    return p[keep], c[~c["event_id"].isin(drop_events)]


def build_catalog(events: pd.DataFrame, picks: pd.DataFrame):
    from obspy import UTCDateTime
    from obspy.core.event import Catalog, CreationInfo, Event, QuantityError, ResourceIdentifier
    from utdquake.bank.utils import get_magnitude, get_origin, get_picks

    by_event = dict(tuple(picks.groupby("event_id")))
    out = []
    for _, row in events.iterrows():
        ev_picks = get_picks(by_event[row["event_id"]])
        origin = get_origin(row, ev_picks)
        ev = Event(resource_id=ResourceIdentifier(id=row["event_id"], prefix="event"),
                   event_type="earthquake", picks=ev_picks, origins=[origin],
                   creation_info=CreationInfo(author=row["agency"], creation_time=UTCDateTime.now()))
        ev.preferred_origin_id = origin.resource_id.id
        if pd.notna(row["magnitude"]):
            mag = get_magnitude(value=row["magnitude"], mag_type="ML", evaluation_mode="automatic",
                                evaluation_status="reviewed", agency=row["agency"], origin_id=origin.resource_id)
            if pd.notna(row["magnitude_error"]):
                mag.mag_errors = QuantityError(uncertainty=float(row["magnitude_error"]))
            ev.magnitudes = [mag]
            ev.preferred_magnitude_id = mag.resource_id.id
        out.append(ev)
    return Catalog(events=out)


def set_pick_agency(root: Path) -> None:
    path = root / "picks" / f"utdq_net={UTDQ_NET}.parquet"
    picks = pd.read_parquet(path)
    picks["pick_agency"] = PICK_AGENCY
    # same dtypes as the other networks' picks tables (str, datetime64[ns])
    for c in picks.columns:
        if isinstance(picks[c].dtype, pd.StringDtype) or picks[c].dtype == object:
            picks[c] = picks[c].astype("str")
        elif pd.api.types.is_datetime64_any_dtype(picks[c]):
            picks[c] = picks[c].astype("datetime64[ns]")
    picks.to_parquet(path, index=False)


def figures(root: Path) -> None:
    """Stats cache (.utdquake/stats/R10.npz) and the standard figure set, into <root>/figures/networks/R10."""
    from utdquake import generate_network_figures
    from utdquake.core.utdquake import Dataset, Network
    Dataset.networks = property(lambda self: self.local_networks)  # the local network table, not the Hub's
    Network(UTDQ_NET).compute_stats(use_cache=False)
    outdir = root / "figures" / "networks" / UTDQ_NET
    saved = generate_network_figures(UTDQ_NET, outdir=outdir, das=False)
    logger.info("%d figures in %s", len(saved), outdir)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--max-events", type=int, default=None)
    ap.add_argument("--event-chunk-size", type=int, default=250)
    ap.add_argument("--figures-only", action="store_true", help="only the stats and figures of a built root")
    args = ap.parse_args()

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

    events, picks = load(args.max_events)
    n_pass = 0
    for i in range(0, len(events), args.event_chunk_size):
        cat = build_catalog(events.iloc[i:i + args.event_chunk_size], picks).apply_utdq_qc()
        n_pass += len(cat)
        if len(cat):
            ebank.put_events(cat)
        logger.info("events %d-%d: %d pass QC so far", i, i + args.event_chunk_size, n_pass)
    logger.info("%d events pass UTDQuake QC; bank holds %d", n_pass, len(ebank.read_index()))

    ebank.put_utdq_stations(stations_df(), das=False, calculate_d_az=True, chunk_seconds=86400)
    ebank.put_utdq_picks(chunk_size=200, apply_utdq_qc=True)

    build_manifests(utdq_nets=[UTDQ_NET], include_events=True, include_stations=True, include_picks=True,
                    include_networks=True, overwrite=True, include_manual_network_info=MANUAL_NETWORK_INFO)
    publish_flat_manifests(root=root)
    build_travel_time_model(UTDQ_NET, local_root=root, update_picks=True)
    set_pick_agency(root)

    ev = pd.read_parquet(root / "events" / f"utdq_net={UTDQ_NET}.parquet")
    sta = pd.read_parquet(root / "stations" / f"utdq_net={UTDQ_NET}.parquet")
    pk = pd.read_parquet(root / "picks" / f"utdq_net={UTDQ_NET}.parquet")
    logger.info("events without picks: %d", (~ev.event_id.isin(pk.event_id)).sum())
    logger.info("check_depth_datum: %s", check_depth_datum(ev, sta) or "OK")
    logger.info("Done: %d events, %d picks, %d stations after QC", len(ev), len(pk), len(sta))
    figures(root)


if __name__ == "__main__":
    main()
