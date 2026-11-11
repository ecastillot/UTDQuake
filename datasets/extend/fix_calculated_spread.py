"""Remove calculated station locations whose spread is larger than MAX_SPREAD_KM, in every network of $UTDQUAKE_ROOT.

A calculated location is the mean of the per-arrival projections (event location + distance + azimuth). From
distant events the projections scatter by hundreds of km (azimuth errors; e.g. IMS arrays in ``at``), and their
mean is meaningless: 38 confirmed stations had a calculated location > 100 km from the confirmed one, and 4
stations without a confirmed location (whose calculated location is the one used) had a spread of 111-9,615 km.
Rule (same 50 km as the ISC IR check): spread = hypot(lat std, lon std) in km > MAX_SPREAD_KM -> calculated
False and the calculated location columns emptied. Picks are not changed (their distances come from the
agencies' arrivals). The network table's station counts are recomputed. Backup: .utdquake/backups/v2.0_spread/.
Rerunning changes nothing. Writes <root>/.utdquake/extend/v2.0/fix_calculated_spread.csv (the stations changed).
"""
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from utdquake.utils.utils import get_network_summary
from utdquake.writers.migrate import _write
from utdquake.writers.schema import PREF_NETWORK_ORDER, PREF_NETWORK_TYPES, PREF_STATIONS_ORDER, PREF_STATIONS_TYPES

MAX_SPREAD_KM = 50.0
COLS = ["calculated_latitude", "calculated_latitude_std", "calculated_longitude", "calculated_longitude_std"]
COUNT_COLS = ["total_stations", "located_stations", "confirmed_stations", "calculated_stations",
              "approx_lat_min", "approx_lat_max", "approx_lon_min", "approx_lon_max"]
root = Path(os.environ["UTDQUAKE_ROOT"])
backup = root / ".utdquake" / "backups" / "v2.0_spread"
table = pd.read_parquet(root / "network" / "network.parquet")
changed = []
for net in table["utdq_net"]:
    path = root / "stations" / f"utdq_net={net}.parquet"
    st = pd.read_parquet(path)
    spread = np.hypot(st["calculated_latitude_std"] * 111.2,
                      st["calculated_longitude_std"] * 111.2 * np.cos(np.radians(st["calculated_latitude"].fillna(0))))
    bad = (spread > MAX_SPREAD_KM).fillna(False)
    if not bad.any():
        continue
    rows = st.loc[bad, ["network", "station", "confirmed"] + COLS + ["calculated_num_entries"]].assign(
        utdq_net=net, spread_km=spread[bad])
    changed.append(rows)
    (backup / "stations").mkdir(parents=True, exist_ok=True)
    if not (backup / "stations" / path.name).exists():
        shutil.copy2(path, backup / "stations" / path.name)
    st.loc[bad, COLS] = np.nan
    st.loc[bad, "calculated"] = False
    _write(st, path, PREF_STATIONS_TYPES, PREF_STATIONS_ORDER)
    ev = pd.read_parquet(root / "events" / f"utdq_net={net}.parquet")
    s = get_network_summary(stations=st, events=ev)
    row = table["utdq_net"] == net
    for c in COUNT_COLS:
        table.loc[row, c] = s[c]
    print(f"{net}: {int(bad.sum())} calculated locations removed "
          f"({int((bad & ~st['confirmed'].fillna(False).astype(bool)).sum())} without a confirmed one)", flush=True)
if changed:
    (backup / "network").mkdir(parents=True, exist_ok=True)
    if not (backup / "network" / "network.parquet").exists():
        shutil.copy2(root / "network" / "network.parquet", backup / "network" / "network.parquet")
    _write(table, root / "network" / "network.parquet", PREF_NETWORK_TYPES, PREF_NETWORK_ORDER)
    out = pd.concat(changed, ignore_index=True)
    out.to_csv(root / ".utdquake" / "extend" / "v2.0" / "fix_calculated_spread.csv", index=False)
    print(f"total: {len(out)} stations in {out.utdq_net.nunique()} networks")
else:
    print("nothing to change")
