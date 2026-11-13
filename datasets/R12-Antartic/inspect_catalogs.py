"""First look at the two Antarctic catalogs (candidate network R12): events, origins, magnitudes, picks,
phases and stations of each QuakeML file. Writes inspect_<file>.csv (one row per pick) and prints a summary.

    python inspect_catalogs.py
"""
from collections import Counter
from pathlib import Path

import pandas as pd
from obspy import read_events

HERE = Path(__file__).resolve().parent
FILES = {"VictoriaLand": HERE / "DG_ABC_quality_cat.xml", "PineIsland": HERE / "PIG_hypoDD_AB_quality.xml"}


def summarize(name, path):
    cat = read_events(str(path))
    ev_rows, pick_rows = [], []
    comments = Counter()
    for ev in cat:
        o = ev.preferred_origin() or ev.origins[0]
        m = ev.preferred_magnitude() or (ev.magnitudes[0] if ev.magnitudes else None)
        for c in ev.comments:
            comments[c.text[:80]] += 1
        ev_rows.append(dict(event_id=str(ev.resource_id), time=o.time.datetime, latitude=o.latitude,
                            longitude=o.longitude, depth_m=o.depth, depth_unc_m=o.depth_errors.uncertainty,
                            n_origins=len(ev.origins), n_mags=len(ev.magnitudes), n_picks=len(ev.picks),
                            n_arrivals=len(o.arrivals), mag=m.mag if m else None,
                            mag_type=m.magnitude_type if m else None, gap=o.quality.azimuthal_gap if o.quality else None,
                            rms=o.quality.standard_error if o.quality else None,
                            method=str(o.method_id) if o.method_id else None, evaluation_mode=o.evaluation_mode))
        phase_of = {str(a.pick_id): a.phase for a in o.arrivals}
        for p in ev.picks:
            w = p.waveform_id
            pick_rows.append(dict(event_id=str(ev.resource_id), network=w.network_code, station=w.station_code,
                                  location=w.location_code, channel=w.channel_code,
                                  phase=p.phase_hint or phase_of.get(str(p.resource_id)), time=p.time.datetime,
                                  in_arrivals=str(p.resource_id) in phase_of, mode=p.evaluation_mode))
    ev, pk = pd.DataFrame(ev_rows), pd.DataFrame(pick_rows)
    pk.to_csv(HERE / f"inspect_{name}_picks.csv", index=False)
    ev.to_csv(HERE / f"inspect_{name}_events.csv", index=False)
    print(f"\n===== {name} ({path.name})")
    print(f"events {len(ev)}  time {ev.time.min()} .. {ev.time.max()}")
    print(f"lat {ev.latitude.min():.2f}..{ev.latitude.max():.2f}  lon {ev.longitude.min():.2f}..{ev.longitude.max():.2f}")
    print(f"depth km: {(ev.depth_m / 1e3).describe().round(1).to_dict()}")
    print(f"origins/event {ev.n_origins.value_counts().to_dict()}  mags/event {ev.n_mags.value_counts().to_dict()}")
    print(f"magnitude {ev.mag.describe().round(2).to_dict()}  types {ev.mag_type.value_counts(dropna=False).to_dict()}")
    print(f"gap {ev.gap.describe().round(0).to_dict()}  rms {ev.rms.describe().round(3).to_dict()}")
    print(f"methods {ev.method.value_counts(dropna=False).head(5).to_dict()}  modes {ev.evaluation_mode.value_counts(dropna=False).to_dict()}")
    print(f"event comments {dict(comments.most_common(5))}")
    print(f"picks {len(pk)} (per event median {ev.n_picks.median():.0f}), in arrivals {pk.in_arrivals.mean():.1%}")
    print(f"phases {pk.phase.value_counts(dropna=False).to_dict()}")
    print(f"pick modes {pk['mode'].value_counts(dropna=False).to_dict()}")
    st = pk.groupby(["network", "station"]).agg(picks=("phase", "size"), first=("time", "min"), last=("time", "max"))
    print(f"networks {pk.network.value_counts().to_dict()}")
    print(f"stations {len(st)}; channels {pk.channel.value_counts().head(8).to_dict()}; locations {pk.location.value_counts(dropna=False).to_dict()}")
    print(st.sort_values("picks", ascending=False).to_string())
    return st


if __name__ == "__main__":
    stations = pd.concat({n: summarize(n, p) for n, p in FILES.items()}, names=["catalog"])
    stations.to_csv(HERE / "inspect_stations.csv")
