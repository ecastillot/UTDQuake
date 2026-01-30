
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Follow-blue?logo=linkedin)](https://www.linkedin.com/in/ecastillot/) ![GitHub followers](https://img.shields.io/github/followers/ecastillot?style=social)  ![GitHub stars](https://img.shields.io/github/stars/ecastillot/UTDQuake?style=social) ![GitHub forks](https://img.shields.io/github/forks/ecastillot/UTDQuake?style=social)



# <span style="background:#E87500; color:white; padding:2px 6px; border-radius:6px;">UTD</span>Quake

University of Texas at Dallas Earthquake Dataset

## Authors
- Emmanuel Castillo (emmanuel.castillotaborda@utdallas.edu)
- Nadine Ushakov (nadine.igonin@utdallas.edu)
- Marine Denolle (mdenolle@uw.edu)


# Dataset

The dataset is available on Hugging Face: **UTDQuake**  

[![Hugging Face Dataset](https://img.shields.io/badge/HuggingFace-Dataset-yellow?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/datasets/ecastillot/UTDQuake)

## Why this dataset matters?

Curated datasets of earthquake **events and phase picks** are essential for modern seismology, especially in the AI era. While waveform datasets have advanced earthquake detection, multistation picks provide complementary information crucial for **phase association** and **earthquake location**.  

This dataset offers structured event catalogs, station metadata, and phase picks across networks, supporting reproducible research and the development of data-driven seismological methods.

## What’s inside?

| Directory   | Format        | Description |
|------------|---------------|-------------|
| `bank/`     | `*.zip`       | ObsPlus `EventBank` datasets, one per network. Can be read directly using [ObsPlus EventBank](https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html). |
| `events/`   | `*.parquet`   | Earthquake event catalogs per network. |
| `stations/` | `*.parquet`   | Station metadata per network. |
| `picks/`    | `*.parquet`   | Seismic phase pick datasets per network. |

For details on the contents and schema of each dataset, please refer to the [Hugging Face dataset viewer](https://huggingface.co/datasets/ecastillot/UTDQuake/viewer).

To get started, see the [Quick Start](#quick-start) section below, or click **“Use this dataset”** on the Hugging Face dataset page for example loading code.


## Quick start

### Basic Access
```python
import utdquake as utdq

# dataset overview 
dataset = utdq.Dataset()
print(dataset)

# network level
network_data = dataset.networks
print(network_data)

dataset.plot_overview(savepath="utdquake.png")
```

### Network Data
```python
# load network 
network = dataset.get_network(name="tx")
print(network)

# events
events = network.events
print(events)

# stations
stations = network.stations
print(stations)

# picks
picks = network.picks
print(picks)
```

### Event Bank
Check [ObsPlus EventBank](https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html) for more details.
```python
# get event bank
ebank = network.bank # 

# Example: Filter by event_id
ev_ids = events["event_id"].iloc[:5].tolist()
cat = ebank.get_events(event_id=ev_ids)
print(cat)

# Example 2: Other filter (check obsplus.EventBank for more details)
cat2 = ebank.get_events(minmagnitude=4.3)
print(cat2)
```


### Plot
```python
# get Obspy Event
network = dataset.get_network(name="tx")
network.plot_overview(savepath="overview.png")
network.plot_uncertainty_boxplots(savepath="uncertainty_boxplots.png")
network.plot_station_location_uncertainty(savepath="station_location_uncertainty.png")
network.plot_stats(savepath="stats.png")
network.plot_pick_histograms(savepath="histograms.png")
network.plot_pick_stats(savepath="pick_stats.png")
```

# Thanks

Thanks to the [UT Dallas HPC team](https://hpc.utdallas.edu/) for providing the computational resources for this dataset.  

We also thank the seismology and AI communities for their work in earthquake research, and Hugging Face for hosting and sharing open datasets.

We welcome feedback and contributions!