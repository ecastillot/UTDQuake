"""Station metadata of the R12 picks from EarthScope (IRIS fdsnws-station, level=channel), for every
(network, station) of the picks in the time span of its picks. Picks with no network code (station ICE)
are looked up by station code alone. Writes raw/stations_channels.csv (one row per channel epoch) and
prints the stations that were not found.

    python get_stations.py     (after inspect_catalogs.py)
"""
from pathlib import Path

import pandas as pd
from obspy import UTCDateTime
from obspy.clients.fdsn import Client

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def main():
    RAW.mkdir(exist_ok=True)
    picks = pd.concat([pd.read_csv(HERE / f"inspect_{n}_picks.csv", dtype={"network": str})
                       for n in ("VictoriaLand", "PineIsland")])
    picks["network"] = picks["network"].fillna("")
    span = picks.groupby(["network", "station"])["time"].agg(["min", "max"]).reset_index()
    client = Client("IRIS")
    rows, missing = [], []
    for _, s in span.iterrows():
        try:
            inv = client.get_stations(network=s.network or "*", station=s.station, level="channel",
                                      starttime=UTCDateTime(s["min"]) - 86400, endtime=UTCDateTime(s["max"]) + 86400)
        except Exception as e:  # noqa: BLE001 - fdsn raises a plain Exception when nothing matches
            missing.append((s.network, s.station, str(e).splitlines()[0][:60]))
            continue
        for net in inv:
            for sta in net:
                for ch in sta:
                    rows.append(dict(pick_network=s.network, network=net.code, station=sta.code,
                                     location=ch.location_code, channel=ch.code, latitude=ch.latitude,
                                     longitude=ch.longitude, elevation=ch.elevation, depth=ch.depth,
                                     start=ch.start_date.datetime, end=ch.end_date.datetime if ch.end_date else None,
                                     sample_rate=ch.sample_rate))
    out = pd.DataFrame(rows)
    out.to_csv(RAW / "stations_channels.csv", index=False)
    found = out.groupby(["pick_network", "station"]).agg(networks=("network", lambda x: ",".join(sorted(set(x)))),
                                                         lat=("latitude", "median"), lon=("longitude", "median"),
                                                         elev=("elevation", "median"),
                                                         lat_spread=("latitude", lambda x: x.max() - x.min()))
    print(found.to_string())
    print(f"\n{len(found)} of {len(span)} stations found; missing: {missing}")


if __name__ == "__main__":
    main()
