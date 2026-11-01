"""
Write the two Colab notebooks of the documentation:

  UTDQuake_Access.ipynb   quickstart: explore the dataset, a network, an event, travel times
  UTDQuake_Upload.ipynb   upload guide: build a UTDQuake network from 100 COSEISMIQ events

Edit the cells here and rerun:  python examples/make_notebooks.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BADGES = (
    "[![Docs](https://img.shields.io/badge/docs-UTDQuake-orange)](https://utdquake.readthedocs.io) "
    "[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97-Dataset-yellow)](https://huggingface.co/datasets/ecastillot/UTDQuake) "
    "[![PyPI](https://img.shields.io/pypi/v/utdquake?color=blue)](https://pypi.org/project/utdquake/) "
    "[![GitHub](https://img.shields.io/badge/GitHub-UTDQuake-black?logo=github)](https://github.com/ecastillot/UTDQuake)"
)
AUTHOR = """---
**Author:** Emmanuel Castillo, University of Texas at Dallas ·
[LinkedIn](https://www.linkedin.com/in/ecastillot/) · [castillo.280997@gmail.com](mailto:castillo.280997@gmail.com)"""


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n")}


def write(name, cells):
    nb = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                       "language_info": {"name": "python"}, "colab": {"provenance": []}}}
    (HERE / name).write_text(json.dumps(nb, indent=1) + "\n")
    print("wrote", HERE / name)


# ------------------------------------------------------------------------------------------- access
ACCESS = [
    md(f"""
# Welcome to **UTD**Quake 🌍
{BADGES}

A global dataset of **earthquakes, stations and seismic phase picks**, ready for machine learning and
seismology.

| | |
|---|---|
| Earthquakes | 346,487 |
| P and S picks | 10.1 million |
| Stations | 17,844 |
| Networks | 82 seismic + 1 DAS |

In this notebook: **1** the dataset · **2** one network · **3** one earthquake · **4** travel times ·
**5** built-in figures.
"""),
    code("!pip install -q utdquake"),
    md("""
## 1. The dataset
Each row is a UTDQuake network (`utdq_net`): who reported the events, the catalog, and how much data it has.
"""),
    code("""
import utdquake as utdq
import matplotlib.pyplot as plt

dataset = utdq.Dataset()
networks = dataset.networks
networks[["utdq_net", "catalog", "country", "events", "p_arrivals", "s_arrivals", "total_stations"]].head(10)
"""),
    code("""
# where the data come from
by_continent = networks.groupby("continent")[["events", "p_arrivals", "s_arrivals"]].sum()
by_continent.sort_values("events").plot.barh(subplots=True, layout=(1, 3), figsize=(13, 3.5),
                                            legend=False, sharex=False, sharey=True, color="#E87500")
plt.tight_layout()
"""),
    md("""
## 2. One network
`get_network` downloads a network the first time (events, stations, picks and its event bank) and reads
it locally afterwards. Here: **tx**, the Texas seismological network (TexNet).
"""),
    code("""
net = dataset.get_network("tx")
events, stations, picks = net.events, net.stations, net.picks
print(f"{len(events)} events, {len(stations)} stations, {len(picks)} picks")
events[["time", "latitude", "longitude", "depth", "magnitude", "p_arrivals", "s_arrivals"]].head()
"""),
    md("Picks join to stations on `(utdq_net, network, station)`, where `network` is the FDSN code of the station:"),
    code("""
picks = picks.merge(stations, on=["utdq_net", "network", "station"], how="left")
picks[["network", "station", "phase", "time", "distance", "travel_time", "travel_time_zscore"]].head()
"""),
    code("""
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# map: events colored by depth, stations as triangles
sc = ax1.scatter(events.longitude, events.latitude, c=events.depth / 1e3, s=12, cmap="viridis_r")
ax1.scatter(stations.confirmed_longitude, stations.confirmed_latitude, marker="^", s=20,
            facecolor="none", edgecolor="k", label="stations")
fig.colorbar(sc, ax=ax1, label="depth (km)")
ax1.set(xlabel="longitude", ylabel="latitude", title="tx: earthquakes and stations")
ax1.legend()

# travel time vs distance, P and S
for phase, color in (("P", "#1f77b4"), ("S", "#E87500")):
    p = picks[picks.phase.str.startswith(phase)]
    ax2.scatter(p.distance * 111.19, p.travel_time, s=1, alpha=0.3, color=color, label=phase)
ax2.set(xlim=(0, 300), ylim=(0, 80), xlabel="epicentral distance (km)", ylabel="travel time (s)",
        title="tx: travel times")
ax2.legend(markerscale=10)
plt.tight_layout()
"""),
    md("""
## 3. One earthquake
Every network comes with an [ObsPy](https://docs.obspy.org) event bank, so you can also get the full
QuakeML events. Here: the largest earthquake and its picks.
"""),
    code("""
big = events.sort_values("magnitude").iloc[-1]
cat = net.bank.get_events(event_id=big.event_id)
print(cat)

ev = picks[picks.event_id == big.event_id]
fig, ax = plt.subplots(figsize=(7, 5))
for phase, color in (("P", "#1f77b4"), ("S", "#E87500")):
    p = ev[ev.phase.str.startswith(phase)]
    ax.scatter(p.travel_time, p.distance * 111.19, color=color, label=phase)
ax.set(xlabel="time after origin (s)", ylabel="distance (km)",
       title=f"M{big.magnitude:.1f}, {str(big.time)[:19]}")
ax.legend()
"""),
    md("""
## 4. Travel times
Each network has a travel-time model fitted to its picks (median and spread by distance). It is also what
`travel_time_zscore` is measured against, to flag unusual picks.
"""),
    code("""
import numpy as np

pred = net.travel_time.predict(phase="P", distance=np.arange(1, 200, 5))   # km
fig, ax = plt.subplots(figsize=(7, 4))
ax.fill_between(pred.distance, pred.travel_time_p1, pred.travel_time_p99, alpha=0.2, label="1-99%")
ax.fill_between(pred.distance, pred.travel_time_p25, pred.travel_time_p75, alpha=0.4, label="25-75%")
ax.plot(pred.distance, pred.travel_time_p50, lw=2, label="median")
ax.set(xlabel="distance (km)", ylabel="P travel time (s)", title="tx: P travel-time model")
ax.legend()
"""),
    md("""
> **Reproducibility.** The dataset is versioned. To always get the data of a given release (e.g. the
> paper's), set `os.environ["UTDQUAKE_REVISION"] = "v1.0"` before downloading.
"""),
    md("""
## 5. Built-in figures
UTDQuake can draw the standard figures of every network. They need [Cartopy](https://cartopy.readthedocs.io)
for the maps.
"""),
    code("!pip install -q cartopy"),
    code("""
net.plot_overview(savepath="tx_overview.png")
net.plot_stats(savepath="tx_stats.png")
"""),
    md(f"""
**Next:** the [quickstart](https://utdquake.readthedocs.io/en/latest/quickstart.html), the figures of all
networks in the [overview](https://utdquake.readthedocs.io/en/latest/overview.html), or
[add your own catalog](https://utdquake.readthedocs.io/en/latest/upload_dataset.html).

{AUTHOR}
"""),
]

# ------------------------------------------------------------------------------------------- upload
UPLOAD = [
    md(f"""
# Upload your catalog to **UTD**Quake 📤
{BADGES}

Build a UTDQuake network from **100 earthquakes of the
[COSEISMIQ](http://coseismiq.ethz.ch) project** (Hengill geothermal area, Iceland): events and picks from
the COSEISMIQ event service, station locations from ETH Zurich. Takes a couple of minutes.

| Step | | |
|---|---|---|
| 1 | `put_events` | events into an event bank |
| 2 | `put_utdq_stations` | station locations |
| 3 | `put_utdq_picks` | picks + quality control |
| 4-5 | `build_manifests` | tables and metadata |
| 6 | `publish_network` | pull request on Hugging Face |
"""),
    code("!pip install -q utdquake cartopy   # cartopy: for the maps"),
    code("""
import os
os.environ["UTDQUAKE_ROOT"] = os.path.abspath("my_utdquake")   # where everything is built
UTDQ_NET = "DEMO"   # your network code: the agency code, or the next free R code (R10, ...)
"""),
    md("""
## Your catalog
Any ObsPy `Catalog` with picks works. Here: 100 manually reviewed events of January 2021.

> ⚠️ **Depths must be below sea level** (QuakeML convention). Correct them first if your catalog uses the
> surface or a well head as reference.
"""),
    code("""
from obspy import UTCDateTime
from obspy.clients.fdsn import Client

cat = Client("http://coseismiq.ethz.ch:8080").get_events(
    contributor="ISOR_manual", starttime=UTCDateTime("2021-01-01"), endtime=UTCDateTime("2021-02-01"),
    limit=100, includearrivals=True)
print(len(cat), "events,", sum(len(e.picks) for e in cat), "picks")
print(cat[0])
"""),
    md("## 1. Event bank"),
    code("""
from utdquake.bank.bank import UTDQBank
from utdquake.core.config import get_utdq_paths

ebank = UTDQBank(base_path=str(get_utdq_paths(UTDQ_NET)["banks"]),
                 path_structure="{year}/{month}/{day}", name_structure="{event_id_end}", format="quakeml")
ebank.put_events(cat)
"""),
    md("## 2. Stations\nOne row per station: `network`, `station`, `latitude`, `longitude`, `elevation`."),
    code("""
import obsplus

networks = sorted({p.waveform_id.network_code for e in cat for p in e.picks})
inv = Client("ETH").get_stations(network=",".join(networks), level="channel",
                                 starttime=UTCDateTime("2021-01-01"), endtime=UTCDateTime("2021-02-01"))
stations = obsplus.stations_to_df(inv).drop_duplicates(["network", "station"])[
    ["network", "station", "latitude", "longitude", "elevation"]]
print(networks, len(stations), "stations")

ebank.put_utdq_stations(stations, calculate_d_az=True)
"""),
    md("## 3. Picks and quality control"),
    code("ebank.put_utdq_picks(apply_utdq_qc=True)"),
    md("""
## 4-5. Tables and metadata
`catalog`, `catalog_type` (`agency`, `research` or `synthetic`) and `dataset_version` are **required**.
"""),
    code("""
import pandas as pd
from utdquake.writers.parquet import build_manifests, publish_flat_manifests

info = pd.DataFrame({
    "utdq_net": [UTDQ_NET],
    "catalog": ["COSEISMIQ"], "catalog_type": ["research"], "dataset_version": ["v2"],
    "provider": ["COSEISMIQ / ETH Zurich"], "provider_url": ["http://coseismiq.ethz.ch"],
    "country": ["Iceland"], "continent": ["Europe"],
    "uploaded_by_github": ["https://github.com/<your-username>"],
})
build_manifests(utdq_nets=[UTDQ_NET], include_events=True, include_stations=True, include_picks=True,
                include_networks=True, overwrite=True, include_manual_network_info=info)
publish_flat_manifests()
"""),
    md("## Your network\nThe same tables every UTDQuake network has:"),
    code("""
root = os.environ["UTDQUAKE_ROOT"]
events = pd.read_parquet(f"{root}/events/utdq_net={UTDQ_NET}.parquet")
stations = pd.read_parquet(f"{root}/stations/utdq_net={UTDQ_NET}.parquet")
picks = pd.read_parquet(f"{root}/picks/utdq_net={UTDQ_NET}.parquet")
print(f"{len(events)} events, {len(stations)} stations, {len(picks)} picks")
pd.read_parquet(f"{root}/network/network.parquet").T.head(20)
"""),
    code("""
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
sc = ax1.scatter(events.longitude, events.latitude, c=events.depth / 1e3, s=25, cmap="viridis_r")
ax1.scatter(stations.confirmed_longitude, stations.confirmed_latitude, marker="^", s=60,
            facecolor="none", edgecolor="k", label="stations")
fig.colorbar(sc, ax=ax1, label="depth (km)")
ax1.set(xlabel="longitude", ylabel="latitude", title="Hengill: earthquakes and stations")
ax1.legend()
for phase, color in (("P", "#1f77b4"), ("S", "#E87500")):
    p = picks[picks.phase.str.startswith(phase)]
    ax2.scatter(p.linear_hyp_distance, p.travel_time, s=8, alpha=0.5, color=color, label=phase)
ax2.set(xlabel="hypocentral distance (km)", ylabel="travel time (s)", title="Travel times")
ax2.legend()
plt.tight_layout()
"""),
    md("""
## Check your network
Before publishing, make sure it looks as expected: the standard UTDQuake figures, and a travel-time model
fitted to your picks. Look for events in the right place and depth, stations where they should be, and
travel times on a clean trend (picks far from it have a high z-score).
"""),
    code("""
import utdquake as utdq
from utdquake.qc.travel_time import build_travel_time_model

build_travel_time_model(UTDQ_NET)   # also adds travel_time_zscore to the picks
net = utdq.Network(UTDQ_NET)
net.plot_overview()
"""),
    code("""
for phase in ("P", "S"):
    net.plot_travel_time_vs_distance_zscore(phase=phase, x_lim=(0, 30), y_lim=(0, 8), add_inset=False)
"""),
    code("net.plot_stats()"),
    md("""
## 6. Publish
Opens a **pull request** on the [UTDQuake dataset](https://huggingface.co/datasets/ecastillot/UTDQuake);
the maintainer reviews and merges it. You need a
[Hugging Face token](https://huggingface.co/settings/tokens) and a real network code (not `DEMO`).
"""),
    code("""
# os.environ["HF_TOKEN"] = "hf_..."
# utdq.publish_network(UTDQ_NET, create_pr=True)
"""),
    md(f"""
Publish the travel-time model too with `utdq.publish_network(UTDQ_NET, include_travel_time=True, create_pr=True)`.
**Optional:** `generate_network_figures` / `publish_network_figures` add your network to the
[overview](https://utdquake.readthedocs.io/en/latest/overview.html). See the
[upload guide](https://utdquake.readthedocs.io/en/latest/upload_dataset.html).

{AUTHOR}
"""),
]

if __name__ == "__main__":
    write("UTDQuake_Access.ipynb", ACCESS)
    write("UTDQuake_Upload.ipynb", UPLOAD)
