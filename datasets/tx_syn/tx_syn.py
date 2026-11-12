"""
Synthetic research network R11 ("tx_syn"): 21,000 synthetic earthquakes in the region of R03 (tx_highres,
Delaware Basin, Texas), each with its own 1D velocity model drawn around DB1D (Monte Carlo), so that a
location model learns to locate through many velocity models.

Steps (each a SLURM job, see run_tx_syn.sh):

    sample       velocity models + hypocenters + the R03 event each copies its stations from  -> work/
    traveltimes  TauP (ObsPy) first-arrival P and S times, one model per event (job array)       -> work/tt/
    build        pick errors, UTDQuake bank / QC / stations / picks / tables, travel-time model and
                 z-scores, stats and figures                                                     -> UTDQuake_txsyn/
    plots        velocity-model PDF (as vel_model.png) and event maps                            -> figures/

Velocity models (``sample_model``): DB1D (db1d.csv) layers, every layer perturbed independently:
    * Vp = DB1D x (1 + shared + per layer): a factor shared by every layer (+-10 %) and one per layer (+-5 %;
      +-15 % in the sediments), so every layer stays centred on DB1D (about +-15 % overall);
    * Vs = Vp / r, r = a shared ratio (uniform 1.6-2.0) + one per layer (+-0.05), clipped to 1.6-2.0: Vs is
      always below Vp (Poisson's ratio >= 0.18);
    * interfaces moved +-1 km (Moho, 40 km, +-3 km), order kept, layers at least 0.5 km thick; sea level (the
      top of the first DB1D layer under the DTM layer) fixed;
    * velocities never decrease with depth below SEDIMENT_BOTTOM_KM (6 km); in the sediments above, a layer
      may be up to LVZ_MAX (10 %) slower than the one above (short low-velocity zones);
    * the last DB1D layer (46 km) extends to 120 km, then IASP91 from 210 km down (TauP needs a whole Earth;
      rays of picks <= 350 km do not go that deep).
The model top is the highest station (TOP_KM above sea level, DTM velocities above sea level); event and
station depths are measured from it.

Hypocenters (``sample_events``): NEAR_FRACTION (70 %) around R03 events (an event drawn at random, moved by
a Gaussian offset of JITTER_KM horizontally and in depth), the rest uniform over the R03 box (lon/lat range of
its events) at 0-15 km. Depth >= 0 km (below sea level). Each synthetic event takes the stations and phases
of the closest R03 event (3D distance): the same stations pick P and S as there, and its magnitude.
Origin times: spread over the R03 period, one every ~3 h, unique.

Picks: true TauP first arrival + error, recipe "local" of hypogt.synthetic.picks (Laplacian, scale 0.05 s P
/ 0.1 s S; 1 % of P and 4 % of S off by 0.4-1.0 / 0.4-1.4 s, either sign). A pick without a TauP arrival
(shadow zone) is dropped. The true travel time and the velocity model of each event are kept
(work/picks_true.parquet, work/models.parquet).

Usage:
    python tx_syn.py sample
    python tx_syn.py traveltimes --task 0 --ntasks 64
    python tx_syn.py build --root ./UTDQuake_txsyn
    python tx_syn.py plots
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s:%(name)s] %(message)s")
logger = logging.getLogger("tx_syn")
logging.getLogger("utdquake.bank.utils").setLevel(logging.WARNING)

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
FIGS = HERE / "figures"
V1_ROOT = Path("/groups/igonin/ecastillo/UTDQuake")    # R03 tables
REF_NET = "R03"

UTDQ_NET = "R11"
N_TARGET = 21000
N_SAMPLE = 21300                     # a few more: events without enough picks (shadow zones, QC) are dropped
SEED = 11
EVENT_AGENCY = "tx_syn"
PICK_AGENCY = "synthetic (TauP, DB1D Monte Carlo)"

VP_SHARED = 0.10                     # Vp: shared factor +-10 %, plus one per layer:
VP_LAYER = 0.05                      #   +-5 % below the sediments,
VP_LAYER_SEDIMENT = 0.15             #   +-15 % in them (where short low-velocity zones are allowed)
VPVS_LAYER = 0.05
VPVS = (1.6, 2.0)
SEDIMENT_BOTTOM_KM = 6.0
LVZ_MAX = 0.10
INTERFACE_JITTER_KM = 1.0
MOHO_KM, MOHO_JITTER_KM = 40.0, 3.0
MIN_THICKNESS_KM = 0.5
TOP_KM = 1.75                        # model top, km above sea level (highest R03 station: 1.705 km)
NEAR_FRACTION = 0.7
JITTER_KM = 1.0
DEPTH_RANGE_KM = (0.0, 15.0)
NOISE = dict(p_scale_s=0.05, s_scale_s=0.1, p_outlier=0.01, s_outlier=0.04, outlier_min_s=0.4,
             p_outlier_max_s=1.0, s_outlier_max_s=1.4)                 # hypogt.synthetic.picks PRESETS["local"]

MANUAL_NETWORK_INFO = pd.DataFrame({
    "utdq_net": [UTDQ_NET],
    "catalog": ["Synthetic Delaware Basin catalog (DB1D Monte Carlo)"],
    "catalog_type": ["synthetic"],
    "dataset_version": ["v2"],
    "provider": ["UTDQuake (synthetic; R03 tx_highres geometry, DB1D Monte Carlo velocity models)"],
    "provider_url": ["https://github.com/ecastillot/UTDQuake"],
    "country": ["U.S.A."],
    "agency": ["Synthetic events, Delaware Basin (TexNet stations of R03)"],
    "continent": ["North America"],
    "uploaded_by_github": ["https://github.com/ecastillot"],
    "contact_email": ["castillo.280997@gmail.com"],
    "doi": ["10.1029/2019JB017727"],        # DB1D: Lomax & Savvaidis (2019), JGR Solid Earth (R03: 10.15781/76hj-ed46)
})


# ----------------------------------------------------------------------------------------------------------
# velocity models

def db1d() -> pd.DataFrame:
    """DB1D layers: top (km below sea level; the DTM layer has top -TOP_KM), vp, vs."""
    d = pd.read_csv(HERE / "db1d.csv", comment="#")
    d.columns = ["top", "vp", "vs"]
    d["top"] = d["top"].replace("DTM", str(-TOP_KM)).astype(float)
    return d.astype(float).reset_index(drop=True)


def sample_model(rng: np.random.Generator, ref: pd.DataFrame) -> pd.DataFrame:
    """One perturbed DB1D (layer tops km below sea level, vp, vs); see the module docstring.

    The whole model is drawn at once and redrawn until it meets the constraints: Vp = DB1D x (1 + g + l),
    g a factor shared by every layer (+-VP_SHARED), l one per layer (+-VP_LAYER, +-VP_LAYER_SEDIMENT in the
    sediments); Vp/Vs = r + m, r shared (VPVS range), m per layer (+-VPVS_LAYER), clipped to VPVS. Drawing
    layer after layer instead (each not slower than the one above) pushes the deep layers above DB1D."""
    tops = ref["top"].to_numpy()
    vp0 = ref["vp"].to_numpy()
    for _ in range(100000):
        new = tops.copy()                                     # interfaces (the DTM top and sea level stay)
        for i in range(2, len(tops)):
            j = MOHO_JITTER_KM if tops[i] == MOHO_KM else INTERFACE_JITTER_KM
            new[i] = tops[i] + rng.uniform(-j, j)
        if not np.all(np.diff(new) >= MIN_THICKNESS_KM):
            continue
        sediment = new < SEDIMENT_BOTTOM_KM
        local = np.where(sediment, rng.uniform(-VP_LAYER_SEDIMENT, VP_LAYER_SEDIMENT, len(new)),
                         rng.uniform(-VP_LAYER, VP_LAYER, len(new)))
        vp = vp0 * (1 + rng.uniform(-VP_SHARED, VP_SHARED) + local)
        ratio = np.clip(rng.uniform(*VPVS) + rng.uniform(-VPVS_LAYER, VPVS_LAYER, len(new)), *VPVS)
        vs = vp / ratio
        drop_vp, drop_vs = vp[1:] / vp[:-1], vs[1:] / vs[:-1]
        deep = ~sediment[1:]                                  # the lower layer of each pair is below the sediments
        if np.any(deep & ((drop_vp < 1) | (drop_vs < 1))):
            continue
        if np.any(~deep & ((drop_vp < 1 - LVZ_MAX) | (drop_vs < 1 - LVZ_MAX))):
            continue
        return pd.DataFrame({"top": new, "vp": vp, "vs": vs})
    raise RuntimeError("could not draw a velocity model")


def write_tvel(model: pd.DataFrame, path: Path) -> None:
    """TauP .tvel: depth from the model top (TOP_KM a.s.l.), the layers, then IASP91 from 210 km."""
    import obspy
    iasp = Path(obspy.__file__).parent / "taup" / "data" / "iasp91.tvel"
    deep = [l.split() for l in iasp.read_text().splitlines()[2:]]
    deep = [tuple(map(float, r)) for r in deep if float(r[0]) >= 210.0]
    rho = lambda vp: 1.74 * vp ** 0.25                         # Gardner, g/cm3 (TauP needs one)
    lines = ["tx_syn", "tx_syn"]
    z = model["top"].to_numpy() + TOP_KM
    for i, r in enumerate(model.itertuples()):
        if i:                                                  # discontinuity: bottom of the layer above
            prev = model.iloc[i - 1]
            lines.append(f"{z[i]:.4f} {prev.vp:.4f} {prev.vs:.4f} {rho(prev.vp):.4f}")
        lines.append(f"{z[i]:.4f} {r.vp:.4f} {r.vs:.4f} {rho(r.vp):.4f}")
    last = model.iloc[-1]
    lines.append(f"{120.0 + TOP_KM:.4f} {last.vp:.4f} {last.vs:.4f} {rho(last.vp):.4f}")
    lines += [f"{d + TOP_KM:.4f} {a:.4f} {b:.4f} {c:.4f}" for d, a, b, c in deep]
    path.write_text("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------------------------------------
# events

def r03():
    ev = pd.read_parquet(V1_ROOT / "events" / f"utdq_net={REF_NET}.parquet",
                         columns=["event_id", "time", "latitude", "longitude", "depth", "magnitude", "magnitude_type"])
    pk = pd.read_parquet(V1_ROOT / "picks" / f"utdq_net={REF_NET}.parquet",
                         columns=["event_id", "network", "station", "phase"])
    st = pd.read_parquet(V1_ROOT / "stations" / f"utdq_net={REF_NET}.parquet")
    st = pd.DataFrame({"network": st["network"].astype(str), "station": st["station"].astype(str),
                       "latitude": st["confirmed_latitude"].fillna(st["calculated_latitude"]),
                       "longitude": st["confirmed_longitude"].fillna(st["calculated_longitude"]),
                       "elevation": st["confirmed_elevation"].fillna(0.0)}).dropna(subset=["latitude", "longitude"])
    st = st.drop_duplicates(["network", "station"]).reset_index(drop=True)
    ev = ev.assign(depth_km=ev["depth"] / 1000.0)
    return ev, pk, st


def _xyz(lat, lon, depth_km, lat0, lon0):
    kx = 111.195 * np.cos(np.radians(lat0))
    return np.c_[(np.asarray(lon) - lon0) * kx, (np.asarray(lat) - lat0) * 111.195, np.asarray(depth_km)]


def sample_events(rng: np.random.Generator, ev: pd.DataFrame, n: int) -> pd.DataFrame:
    from scipy.spatial import cKDTree
    lat0, lon0 = ev["latitude"].mean(), ev["longitude"].mean()
    kx = 111.195 * np.cos(np.radians(lat0))
    box = dict(lat=(ev["latitude"].min(), ev["latitude"].max()), lon=(ev["longitude"].min(), ev["longitude"].max()))
    n_near = int(round(n * NEAR_FRACTION))
    rows = []
    while sum(len(r) for r in rows) < n_near:                   # near R03 events
        k = n_near
        src = ev.iloc[rng.integers(0, len(ev), k)]
        lat = src["latitude"].to_numpy() + rng.normal(0, JITTER_KM, k) / 111.195
        lon = src["longitude"].to_numpy() + rng.normal(0, JITTER_KM, k) / kx
        dep = src["depth_km"].to_numpy() + rng.normal(0, JITTER_KM, k)
        ok = dep >= 0
        rows.append(pd.DataFrame({"latitude": lat[ok], "longitude": lon[ok], "depth_km": dep[ok], "kind": "near"}))
    near = pd.concat(rows, ignore_index=True).iloc[:n_near]
    m = n - n_near
    uni = pd.DataFrame({"latitude": rng.uniform(*box["lat"], m), "longitude": rng.uniform(*box["lon"], m),
                        "depth_km": rng.uniform(*DEPTH_RANGE_KM, m), "kind": "uniform"})
    out = pd.concat([near, uni], ignore_index=True)
    out = out.iloc[rng.permutation(len(out))].reset_index(drop=True)
    tree = cKDTree(_xyz(ev["latitude"], ev["longitude"], ev["depth_km"], lat0, lon0))
    d, j = tree.query(_xyz(out["latitude"], out["longitude"], out["depth_km"], lat0, lon0))
    out["ref_event_id"] = ev["event_id"].to_numpy()[j]
    out["ref_distance_km"] = d
    out["magnitude"] = ev["magnitude"].to_numpy()[j]
    out["magnitude_type"] = ev["magnitude_type"].astype(str).to_numpy()[j]
    t0, t1 = ev["time"].min(), ev["time"].max()
    step = (t1 - t0) / len(out)
    out["time"] = t0 + step * np.arange(len(out)) + pd.to_timedelta(rng.uniform(0, 0.5, len(out)) * step.total_seconds(),
                                                                     unit="s")
    out.insert(0, "event_id", [f"txsyn_{i:05d}" for i in range(len(out))])
    return out


def cmd_sample(args):
    WORK.mkdir(exist_ok=True)
    rng = np.random.default_rng(SEED)
    ev, pk, st = r03()
    events = sample_events(rng, ev, N_SAMPLE)
    ref = db1d()
    models = []
    for eid in events["event_id"]:
        m = sample_model(rng, ref)
        m.insert(0, "layer", range(len(m)))
        m.insert(0, "event_id", eid)
        models.append(m)
    models = pd.concat(models, ignore_index=True)
    # the stations and phases each event copies: those of its R03 event
    want = events[["event_id", "ref_event_id"]].merge(pk.rename(columns={"event_id": "ref_event_id"}), on="ref_event_id")
    want["phase"] = want["phase"].astype(str).str.upper().str[0]
    want = want[want["phase"].isin(["P", "S"])].drop_duplicates(["event_id", "network", "station", "phase"])
    want = want.merge(st, on=["network", "station"], how="inner")
    events.to_parquet(WORK / "events.parquet", index=False)
    models.to_parquet(WORK / "models.parquet", index=False)
    want.to_parquet(WORK / "wanted_picks.parquet", index=False)
    st.to_parquet(WORK / "stations.parquet", index=False)
    logger.info("%d events (%d near R03, %d uniform), %d models, %d picks wanted (%d P, %d S)", len(events),
                (events.kind == "near").sum(), (events.kind == "uniform").sum(), len(models) // len(ref),
                len(want), (want.phase == "P").sum(), (want.phase == "S").sum())


# ----------------------------------------------------------------------------------------------------------
# travel times

P_PHASES = ["p", "P", "Pn", "Pg"]
S_PHASES = ["s", "S", "Sn", "Sg"]


def cmd_traveltimes(args):
    from obspy.geodetics import locations2degrees
    from obspy.taup import TauPyModel
    from obspy.taup.taup_create import build_taup_model

    events = pd.read_parquet(WORK / "events.parquet")
    models = pd.read_parquet(WORK / "models.parquet")
    want = pd.read_parquet(WORK / "wanted_picks.parquet")
    mine = events.iloc[args.task::args.ntasks]
    out_path = Path(args.tt_dir) / f"tt_{args.task:03d}.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = pd.read_parquet(out_path) if out_path.exists() else pd.DataFrame()
    finished = set(done["event_id"]) if len(done) else set()
    rows = [done] if len(done) else []
    tmp = Path(tempfile.mkdtemp(prefix=f"txsyn_{args.task}_"))
    by_event_m, by_event_w = dict(tuple(models.groupby("event_id"))), dict(tuple(want.groupby("event_id")))
    try:
        for k, e in enumerate(mine.itertuples()):
            if e.event_id in finished or e.event_id not in by_event_w:
                continue
            tvel = tmp / "m.tvel"
            write_tvel(by_event_m[e.event_id][["top", "vp", "vs"]], tvel)
            build_taup_model(str(tvel), output_folder=str(tmp), verbose=False)
            tm = TauPyModel(str(tmp / "m.npz"))
            w = by_event_w[e.event_id]
            tt, ph = [], []
            for r in w.itertuples():
                dist = locations2degrees(e.latitude, e.longitude, r.latitude, r.longitude)
                arr = tm.get_travel_times(source_depth_in_km=e.depth_km + TOP_KM, distance_in_degree=dist,
                                          phase_list=P_PHASES if r.phase == "P" else S_PHASES,
                                          receiver_depth_in_km=max(TOP_KM - r.elevation / 1000.0, 0.0))
                first = min(arr, key=lambda a: a.time) if len(arr) else None
                tt.append(first.time if first else np.nan)
                ph.append(first.name if first else None)
            rows.append(w.assign(travel_time_true=tt, taup_phase=ph))
            if (k + 1) % 50 == 0:                               # checkpoint
                pd.concat(rows, ignore_index=True).to_parquet(out_path, index=False)
                logger.info("task %d: %d/%d events", args.task, k + 1, len(mine))
        pd.concat(rows, ignore_index=True).to_parquet(out_path, index=False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    logger.info("task %d done: %d events", args.task, len(mine))


# ----------------------------------------------------------------------------------------------------------
# build

def add_errors(tt: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    is_p = (tt["phase"] == "P").to_numpy()
    scale = np.where(is_p, NOISE["p_scale_s"], NOISE["s_scale_s"])
    err = rng.laplace(0, 1, len(tt)) * scale
    bad = rng.random(len(tt)) < np.where(is_p, NOISE["p_outlier"], NOISE["s_outlier"])
    hi = np.where(is_p, NOISE["p_outlier_max_s"], NOISE["s_outlier_max_s"])
    extra = rng.uniform(NOISE["outlier_min_s"], hi) * rng.choice([-1.0, 1.0], len(tt))
    return np.where(bad, err + extra, err)


def load_synthetics(tt_dir: Path = WORK / "tt"):
    events = pd.read_parquet(WORK / "events.parquet")
    tt = pd.concat([pd.read_parquet(p) for p in sorted(Path(tt_dir).glob("tt_*.parquet"))], ignore_index=True)
    tt = tt.dropna(subset=["travel_time_true"]).drop_duplicates(["event_id", "network", "station", "phase"])
    rng = np.random.default_rng(SEED + 1)
    tt["error_s"] = add_errors(tt, rng)
    tt = tt.merge(events[["event_id", "time"]], on="event_id")
    tt["pick_time"] = tt["time"] + pd.to_timedelta(tt["travel_time_true"] + tt["error_s"], unit="s")
    # the UTDQuake event QC: >= 4 phases and >= 3 stations
    n = tt.groupby("event_id").agg(phases=("phase", "size"), stations=("station", "nunique"))
    ok = n[(n.phases >= 4) & (n.stations >= 3)].index
    events = events[events["event_id"].isin(ok)].head(N_TARGET)
    tt = tt[tt["event_id"].isin(events["event_id"])]
    logger.info("%d events with enough picks (target %d), %d picks", len(events), N_TARGET, len(tt))
    tt.drop(columns=["time"]).to_parquet(WORK / "picks_true.parquet", index=False)
    picks = pd.DataFrame({"agency": PICK_AGENCY, "event_id": tt["event_id"], "network": tt["network"],
                          "station": tt["station"], "location": None, "instrument_type": "HH",
                          "phase": tt["phase"], "pick_time": tt["pick_time"]})
    ev = pd.DataFrame({"agency": EVENT_AGENCY, "event_id": events["event_id"], "origin_time": events["time"],
                       "latitude": events["latitude"], "longitude": events["longitude"],
                       "depth[km]": events["depth_km"], "magnitude": events["magnitude"],
                       "magnitude_type": events["magnitude_type"]}).reset_index(drop=True)
    return ev, picks.reset_index(drop=True)


def build_catalog(events: pd.DataFrame, picks: pd.DataFrame):
    from obspy import UTCDateTime
    from obspy.core.event import Catalog, Comment, CreationInfo, Event, ResourceIdentifier
    from utdquake.bank.utils import get_magnitude, get_origin, get_picks

    by_event = dict(tuple(picks.groupby("event_id")))
    out = []
    for _, row in events.iterrows():
        ev_picks = get_picks(by_event[row["event_id"]])
        origin = get_origin(row, ev_picks)
        ev = Event(resource_id=ResourceIdentifier(id=row["event_id"], prefix="event"),
                   event_type="earthquake", picks=ev_picks, origins=[origin],
                   comments=[Comment(text="synthetic event (tx_syn): TauP picks through its own DB1D Monte Carlo "
                                          "velocity model")],
                   creation_info=CreationInfo(author=row["agency"], creation_time=UTCDateTime.now()))
        ev.preferred_origin_id = origin.resource_id.id
        mag = get_magnitude(value=row["magnitude"], mag_type=row["magnitude_type"], evaluation_mode="automatic",
                            evaluation_status="reviewed", agency=row["agency"], origin_id=origin.resource_id)
        ev.magnitudes = [mag]
        ev.preferred_magnitude_id = mag.resource_id.id
        out.append(ev)
    return Catalog(events=out)


def set_pick_agency(root: Path) -> None:
    path = root / "picks" / f"utdq_net={UTDQ_NET}.parquet"
    picks = pd.read_parquet(path)
    picks["pick_agency"] = PICK_AGENCY
    for c in picks.columns:
        if isinstance(picks[c].dtype, pd.StringDtype) or picks[c].dtype == object:
            picks[c] = picks[c].astype("str")
        elif pd.api.types.is_datetime64_any_dtype(picks[c]):
            picks[c] = picks[c].astype("datetime64[ns]")
    picks.to_parquet(path, index=False)


def figures(root: Path) -> None:
    from utdquake import generate_network_figures
    from utdquake.core.utdquake import Network
    Network(UTDQ_NET).compute_stats(use_cache=False)
    outdir = root / "figures" / "networks" / UTDQ_NET
    saved = generate_network_figures(UTDQ_NET, outdir=outdir, das=False)
    logger.info("%d figures in %s", len(saved), outdir)


DESCRIPTION = """\
R11 -- Synthetic Delaware Basin catalog (tx_syn), UTDQuake {version}
=====================================================================

WHAT IT IS
  {n_events:,} SYNTHETIC earthquakes (not real events) in the Delaware Basin, West Texas, made to teach
  earthquake-location models to locate through many different velocity models. Every event has its own
  1D velocity model (Monte Carlo around DB1D); its P and S picks are travel times through that model plus
  pick errors. Station geometry, pick patterns and magnitudes come from the real research catalog R03
  (TexNet High Resolution Earthquake Catalog, Bureau of Economic Geology, University of Texas at Austin,
  doi:10.15781/76hj-ed46). DB1D: Lomax & Savvaidis (2019), JGR Solid Earth, doi:10.1029/2019JB017727.

  Events {n_events:,} | picks {n_picks:,} (P {n_p:,}, S {n_s:,}) | stations {n_sta} | origin times spread over
  {t0} - {t1} (one every ~3 h; they are not real times).

HOW IT WAS MADE  (code: datasets/tx_syn/tx_syn.py in github.com/ecastillot/UTDQuake)
  1. Velocity model, one per event, drawn independently (seed {seed}):
     - reference: DB1D, the Delaware Basin 1D velocity model of Lomax & Savvaidis (2019), Improving
       Absolute Earthquake Location in West Texas Using Probabilistic, Proxy Ground-Truth Station
       Corrections, J. Geophys. Res. Solid Earth 124(11), 11447-11465, doi:10.1029/2019JB017727; file as
       shared by Castillo, Ushakov & Savvaidis (2026), Seismological Research Letters,
       doi:10.1785/0220250288 (vp/DB_model.csv of huggingface.co/datasets/ecastillot/CMEZ-SPHighResCatalog).
       Layers at {tops} km below sea level, plus a DTM layer from the surface to sea level. Below 46 km: the
       last DB1D layer to 120 km, IASP91 from 210 km.
     - Vp = DB1D x (1 + g + l): g shared by every layer, uniform +-{vp_shared:.0%}; l per layer, uniform +-{vp_layer:.0%}
       (+-{vp_sed:.0%} in the sediments, above {sed:.0f} km). About +-15 % overall around DB1D.
     - Vs = Vp / (r + m): r shared, uniform {r0}-{r1}; m per layer +-{r_layer}; Vp/Vs kept within {r0}-{r1}, so
       Vs is always below Vp.
     - Interfaces moved uniform +-{jit:.0f} km (Moho, 40 km: +-{moho:.0f} km); layers at least {thick} km thick.
     - Velocity never decreases with depth below {sed:.0f} km; above (sediments) a layer can be up to
       {lvz:.0%} slower than the one above (short low-velocity zones). A model breaking a rule is redrawn.
     - Result: median Vp per layer within ~4 % of DB1D; Vp/Vs {vpvs_min:.2f}-{vpvs_max:.2f}.
  2. Hypocenters:
     - {near:.0%} near R03 events: a random R03 event moved by a Gaussian offset (sd {jitter:.0f} km in x, y and depth);
     - {uni:.0%} uniform over the R03 area ({lat0:.2f}-{lat1:.2f} N, {lon0:.2f} - {lon1:.2f} E), depth {d0:.0f}-{d1:.0f} km;
     - depths below sea level (>= 0 km).
  3. Stations and picks: each synthetic event copies the stations and phases (P, S) of the closest R03
     event (3D distance) -- the same stations pick P and S as there -- and its magnitude (ML, copied, not
     measured).
  4. Travel times: ObsPy TauP, first arrival among p/P/Pn/Pg (S: s/S/Sn/Sg) through the event's own
     model; model top at {top} km above sea level, station and event depths measured from it (station
     elevations kept). Picks without an arrival are dropped ({n_nan} of {n_wanted:,}).
  5. Pick errors (recipe "local" of hypogt.synthetic.picks): Laplacian, scale {p_s} s (P) / {s_s} s (S);
     {p_out:.0%} of P and {s_out:.0%} of S picks off by an extra {o0}-{p_max} s / {o0}-{s_max} s (either sign).
  6. UTDQuake pipeline as for every network: event QC, station distances/azimuths, pick QC, tables,
     travel-time model and z-scores, stats and figures. Events kept: the first {n_events:,} with >= 4 picks
     on >= 3 stations (of {n_sampled:,} drawn).

KNOWN LIMITS
  - 1D models only (no lateral changes); first arrivals only.
  - Magnitudes and the station/phase pattern are those of the nearest real event, not of the synthetic
    location; uniform events far from the seismicity copy an event up to ~{ref_max:.0f} km away (median {ref_med:.1f} km).
  - Origin times are artificial.

FILES
  Per-event true velocity models and true travel times: work/models.parquet, work/picks_true.parquet
  (datasets/tx_syn). Event ids txsyn_00000 ... ; pick agency "{pick_agency}".
"""


def write_description(root: Path) -> Path:
    """<root>/figures/networks/R11/R11_catalog_description.txt: how the catalog was made, with its numbers."""
    ev = pd.read_parquet(root / "events" / f"utdq_net={UTDQ_NET}.parquet", columns=["event_id", "time"])
    pk = pd.read_parquet(root / "picks" / f"utdq_net={UTDQ_NET}.parquet", columns=["phase"])
    st = pd.read_parquet(root / "stations" / f"utdq_net={UTDQ_NET}.parquet", columns=["station"])
    models = pd.read_parquet(WORK / "models.parquet")
    sampled = pd.read_parquet(WORK / "events.parquet")
    kept = sampled[sampled["event_id"].isin(ev["event_id"].str.replace("smi:local/", "", regex=False))]
    want = pd.read_parquet(WORK / "wanted_picks.parquet", columns=["event_id"])
    tt = pd.concat([pd.read_parquet(p, columns=["travel_time_true"]) for p in sorted((WORK / "tt").glob("tt_*.parquet"))])
    ref, ev0 = db1d(), r03()[0]
    vpvs = models["vp"] / models["vs"]
    text = DESCRIPTION.format(
        version=MANUAL_NETWORK_INFO["dataset_version"].iat[0], n_events=len(ev), n_picks=len(pk),
        n_p=int((pk.phase == "P").sum()), n_s=int((pk.phase == "S").sum()), n_sta=len(st),
        t0=pd.Timestamp(ev["time"].min()).date(), t1=pd.Timestamp(ev["time"].max()).date(), seed=SEED,
        tops=", ".join(f"{t:g}" for t in ref["top"].iloc[1:]), vp_shared=VP_SHARED, vp_layer=VP_LAYER,
        vp_sed=VP_LAYER_SEDIMENT, sed=SEDIMENT_BOTTOM_KM, r0=VPVS[0], r1=VPVS[1], r_layer=VPVS_LAYER,
        jit=INTERFACE_JITTER_KM, moho=MOHO_JITTER_KM, thick=MIN_THICKNESS_KM, lvz=LVZ_MAX,
        vpvs_min=vpvs.min(), vpvs_max=vpvs.max(), near=NEAR_FRACTION, uni=1 - NEAR_FRACTION, jitter=JITTER_KM,
        lat0=ev0.latitude.min(), lat1=ev0.latitude.max(), lon0=ev0.longitude.min(), lon1=ev0.longitude.max(),
        d0=DEPTH_RANGE_KM[0], d1=DEPTH_RANGE_KM[1], top=TOP_KM, n_nan=int(tt["travel_time_true"].isna().sum()),
        n_wanted=len(want), p_s=NOISE["p_scale_s"], s_s=NOISE["s_scale_s"], p_out=NOISE["p_outlier"],
        s_out=NOISE["s_outlier"], o0=NOISE["outlier_min_s"], p_max=NOISE["p_outlier_max_s"],
        s_max=NOISE["s_outlier_max_s"], n_sampled=len(sampled), ref_max=kept["ref_distance_km"].max(),
        ref_med=kept["ref_distance_km"].median(), pick_agency=PICK_AGENCY)
    out = root / "figures" / "networks" / UTDQ_NET / f"{UTDQ_NET}_catalog_description.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    logger.info("description: %s", out)
    return out


def cmd_build(args):
    os.environ["UTDQUAKE_ROOT"] = args.root
    root = Path(args.root)
    if args.figures_only:
        return figures(root)
    if args.describe_only:
        return write_description(root)
    from utdquake.bank.bank import UTDQBank
    from utdquake.core.config import get_utdq_paths
    from utdquake.hub import check_depth_datum
    from utdquake.qc.travel_time import build_travel_time_model
    from utdquake.writers.parquet import build_manifests, publish_flat_manifests

    events, picks = load_synthetics(args.tt_dir)
    if args.max_events:
        events = events.head(args.max_events)
        picks = picks[picks["event_id"].isin(events["event_id"])]
    ebank = UTDQBank(base_path=str(get_utdq_paths(UTDQ_NET)["banks"]), path_structure="{year}/{month}/{day}",
                     name_structure="{event_id_end}", format="quakeml")
    n_pass = 0
    for i in range(0, len(events), 250):
        cat = build_catalog(events.iloc[i:i + 250], picks).apply_utdq_qc()
        n_pass += len(cat)
        if len(cat):
            ebank.put_events(cat)
    logger.info("%d of %d events pass UTDQuake QC", n_pass, len(events))
    st = pd.read_parquet(WORK / "stations.parquet")
    st = st[st.set_index(["network", "station"]).index.isin(picks.set_index(["network", "station"]).index)]
    ebank.put_utdq_stations(st, das=False, calculate_d_az=True, chunk_seconds=86400 * 30)
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
    logger.info("Done: %d events, %d picks (%d P, %d S), %d stations", len(ev), len(pk),
                (pk.phase == "P").sum(), (pk.phase == "S").sum(), len(sta))
    figures(root)


# ----------------------------------------------------------------------------------------------------------
# plots

def profile(model: pd.DataFrame, z: np.ndarray, col: str) -> np.ndarray:
    tops = model["top"].to_numpy()
    i = np.clip(np.searchsorted(tops, z, side="right") - 1, 0, len(tops) - 1)
    return model[col].to_numpy()[i]


def cmd_plots(args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIGS.mkdir(exist_ok=True)
    models = pd.read_parquet(WORK / "models.parquet")
    ref = db1d()
    z = np.linspace(-TOP_KM, 50, 400)
    vbins = np.linspace(0, 10, 101)
    fig, axes = plt.subplots(1, 2, figsize=(9, 5.5), sharey=True)
    for ax, col, color, name in ((axes[0], "vp", "k", "VP"), (axes[1], "vs", "r", "VS")):
        prof = np.stack([profile(m, z, col) for _, m in models.groupby("event_id")])
        h = np.stack([np.histogram(prof[:, k], bins=vbins)[0] for k in range(len(z))]).astype(float)
        h /= h.max(axis=1, keepdims=True)
        im = ax.pcolormesh(0.5 * (vbins[1:] + vbins[:-1]), z, h, cmap="viridis", vmin=0, vmax=1, shading="nearest")
        for _, m in list(models.groupby("event_id"))[:5]:
            ax.plot(profile(m, z, col), z, color="w", lw=0.6, alpha=0.8)
        ax.plot(profile(ref, z, col), z, color=color, lw=2, label="DB1D")
        ax.set_title(f"{name} (km/s), {models.event_id.nunique():,} models")
        ax.set_xlabel("Velocity (km/s)")
        ax.grid(alpha=0.3)
        ax.legend(loc="lower left")
    axes[0].set_ylabel("Depth below sea level (km)")
    axes[0].invert_yaxis()
    fig.colorbar(im, ax=axes, label="PDF (normalised per depth)")
    fig.savefig(FIGS / "velocity_models.png", dpi=150, bbox_inches="tight")
    # Vp/Vs and checks
    models["vpvs"] = models["vp"] / models["vs"]
    q = models.groupby("layer").agg(top=("top", "median"), vp_p05=("vp", lambda v: v.quantile(.05)),
                                    vp_med=("vp", "median"), vp_p95=("vp", lambda v: v.quantile(.95)),
                                    vs_med=("vs", "median"), vpvs_med=("vpvs", "median"))
    q["db1d_vp"], q["db1d_vs"] = ref["vp"].to_numpy(), ref["vs"].to_numpy()
    logger.info("per layer:\n%s", q.round(3).to_string())
    logger.info("Vp/Vs min %.3f max %.3f; Vp < Vs anywhere: %d", models.vpvs.min(), models.vpvs.max(),
                (models.vp <= models.vs).sum())
    # event map against R03
    events = pd.read_parquet(WORK / "events.parquet")
    ev, _, st = r03()
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.5))
    ax[0].scatter(st.longitude, st.latitude, marker="^", c="g", s=12, label="R03 stations")
    for kind, c in (("near", "tab:orange"), ("uniform", "tab:blue")):
        e = events[events.kind == kind]
        ax[0].scatter(e.longitude, e.latitude, s=1, c=c, alpha=0.3, label=f"synthetic {kind} ({len(e):,})")
        ax[1].scatter(e.longitude, e.depth_km, s=1, c=c, alpha=0.3)
    ax[0].scatter(ev.longitude, ev.latitude, s=1, c="k", alpha=0.3, label=f"R03 ({len(ev):,})")
    ax[1].scatter(ev.longitude, ev.depth_km, s=1, c="k", alpha=0.3)
    ax[0].legend(markerscale=6, fontsize=8)
    ax[0].set_xlabel("Longitude")
    ax[0].set_ylabel("Latitude")
    ax[1].invert_yaxis()
    ax[1].set_xlabel("Longitude")
    ax[1].set_ylabel("Depth (km)")
    fig.savefig(FIGS / "events_map.png", dpi=150, bbox_inches="tight")
    logger.info("figures in %s", FIGS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="step", required=True)
    sub.add_parser("sample")
    t = sub.add_parser("traveltimes")
    t.add_argument("--task", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    t.add_argument("--ntasks", type=int, default=64)
    t.add_argument("--tt-dir", default=str(WORK / "tt"))
    b = sub.add_parser("build")
    b.add_argument("--root", required=True)
    b.add_argument("--max-events", type=int, default=None)
    b.add_argument("--figures-only", action="store_true")
    b.add_argument("--describe-only", action="store_true", help="only the catalog description next to the figures")
    b.add_argument("--tt-dir", default=str(WORK / "tt"))
    sub.add_parser("plots")
    args = ap.parse_args()
    {"sample": cmd_sample, "traveltimes": cmd_traveltimes, "build": cmd_build, "plots": cmd_plots}[args.step](args)


if __name__ == "__main__":
    main()
