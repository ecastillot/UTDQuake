"""Totals of the local dataset (seismic networks) for docs/source/versions.rst; writes totals_v2.0.csv."""
import os
from pathlib import Path
import pandas as pd
from utdquake.utils.utils import get_network_summary
R = Path(os.environ["UTDQUAKE_ROOT"])
t = pd.read_parquet(R / "network" / "network.parquet")
nets = sorted(t.utdq_net)
st = pd.concat([pd.read_parquet(R / f"stations/utdq_net={n}.parquet") for n in nets])
ev = pd.concat([pd.read_parquet(R / f"events/utdq_net={n}.parquet", columns=["latitude", "longitude", "time", "p_phase_count", "s_phase_count", "dataset_version"]) for n in nets])
ph, src = [], 0
for n in nets:
    p = pd.read_parquet(R / f"picks/utdq_net={n}.parquet", columns=["phase", "network_source"])
    ph.append(p.phase.astype(str).value_counts()); src += int((p.network_source == "unresolved_ir").sum())
ph = pd.concat(ph).groupby(level=0).sum()
s = get_network_summary(stations=st, events=ev, distinct_stations=True)
P = {k: int(ph.get(k, 0)) for k in ("P", "Pg", "Pn")}; S = {k: int(ph.get(k, 0)) for k in ("S", "Sg", "Sn")}
ptype = int(ph[ph.index.str.upper().str.startswith("P")].sum()); stype = int(ph[ph.index.str.upper().str.startswith("S")].sum())
out = {"networks": len(nets), "events": len(ev), "events_v1": int((ev.dataset_version == "v1").sum()),
       "events_v2": int((ev.dataset_version == "v2").sum()), "picks": int(ph.sum()), "p_type": ptype, **P,
       "s_type": stype, **S, "stations": s["total_stations"], "located": s["located_stations"],
       "confirmed": s["confirmed_stations"], "unresolved_ir_picks": src}
pd.Series(out).to_csv(R / ".utdquake" / "extend" / "v2.0" / "totals_v2.0.csv")
print(pd.Series(out).to_string())
