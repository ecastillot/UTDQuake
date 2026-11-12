
[![PyPI](https://img.shields.io/pypi/v/utdquake?color=orange&label=PyPI&style=flat)](https://pypi.org/project/utdquake/) ![GitHub stars](https://img.shields.io/github/stars/ecastillot/UTDQuake?style=social) ![GitHub forks](https://img.shields.io/github/forks/ecastillot/UTDQuake?style=social) ![GitHub followers](https://img.shields.io/github/followers/ecastillot?style=social) [![LinkedIn](https://img.shields.io/badge/LinkedIn-Follow-blue?logo=linkedin)](https://www.linkedin.com/in/ecastillot/) 


<img src="https://raw.githubusercontent.com/ecastillot/UTDQuake/main/docs/source/_static/logo/utdquake_logo_ok.png" alt="seismonitor" width="150"> 

<!--
# <span style="background:#E87500; color:white; padding:2px 6px; border-radius:6px;">UTD</span>Quake
-->

[![Hugging Face Dataset](https://img.shields.io/badge/HuggingFace-Dataset-yellow?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/datasets/ecastillot/UTDQuake)  [![Read the Docs](https://img.shields.io/badge/Docs-Read%20the%20Docs-blue?style=for-the-badge&logo=read-the-docs)](https://utdquake.readthedocs.io/en/latest/index.html) 

**University of Texas at Dallas Earthquake Dataset**

A global earthquake dataset constructed from high-quality source and receiver metadata, including associated seismic phase picks across diverse station geometries.

![utdquake](https://raw.githubusercontent.com/ecastillot/UTDQuake/main/figures/utdquake_overview_stats.png)

# Documentation

Full documentation for UTDQuake is available here: 

 [![Read the Docs](https://img.shields.io/badge/Docs-Read%20the%20Docs-blue?style=for-the-badge&logo=read-the-docs)](https://utdquake.readthedocs.io/en/latest/index.html)

You will see:

- QuickStart guide to get you up and running  
- Detailed API reference  
- Tutorials and example workflows  

# Dataset

The dataset is available on Hugging Face: **UTDQuake**  

[![Hugging Face Dataset](https://img.shields.io/badge/HuggingFace-Dataset-yellow?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/datasets/ecastillot/UTDQuake)


## Installation ([utdquake](https://pypi.org/project/utdquake))
```bash
pip install utdquake
```

## Why this dataset matters?

Curated datasets of earthquake **events and phase picks** are essential for modern seismology, especially in the AI era. While waveform datasets have advanced earthquake detection, multistation picks provide complementary information crucial for **phase association** and **earthquake location**.  

This dataset offers structured event catalogs, station metadata, and phase picks across networks, supporting reproducible research and the development of data-driven seismological methods.

## What’s inside?

| Directory   | Format        | Description |
|------------|---------------|-------------|
| `network/`   | `*.parquet`   | Network metadata, one row per UTDQuake network (`utdq_net`). |
| `events/`   | `*.parquet`   | Earthquake events, one file per `utdq_net`. |
| `stations/` | `*.parquet`   | Station metadata, one file per `utdq_net`. |
| `picks/`    | `*.parquet`   | Seismic phase picks, one file per `utdq_net`. |
| `banks/`     | `*.zip`       | ObsPlus `EventBank` datasets, one per `utdq_net`. Can be read directly using [ObsPlus EventBank](https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html). |

**Naming.** `utdq_net` is the UTDQuake network: the monitoring network or project that reported the events and picks (e.g. `tx`, `AEIC`, `R05`); it is the key that links the four tables. `catalog` (network table) is the catalog or bulletin the events come from. `network` (stations and picks tables) is the FDSN network code of each station, as in the pick's `seed_id`. Join picks to stations on `(utdq_net, network, station)`.

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
# load a network by its utdq_net code
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

# Authors

<table>
  <tr>
    <td valign="middle">
      <strong>Emmanuel Castillo</strong><br>
      University of Texas at Dallas<br>
      <a href="https://www.linkedin.com/in/ecastillot/" target="_blank">
        <img src="https://img.shields.io/badge/LinkedIn-Follow-blue?logo=linkedin&logoColor=white&style=flat" height="20">
      </a>
      <a href="mailto:castillo.280997@gmail.com" target="_blank">
        <img src="https://img.shields.io/badge/Email-Send-red?logo=gmail&logoColor=white&style=flat" height="20">
      </a>
    </td>
    <td width="100" align="center">
      <img src="https://raw.githubusercontent.com/ecastillot/UTDQuake/main/docs/source/_static/photos/emmanuel.jpg" alt="Emmanuel" width="80" height="80" style="border-radius:50%; object-fit:cover;">
    </td>
  </tr>
  <tr>
    <td valign="middle">
      <strong>Nadine Ushakov</strong><br>
      University of Texas at Dallas<br>
      <a href="https://www.linkedin.com/in/nadineushakov/" target="_blank">
        <img src="https://img.shields.io/badge/LinkedIn-Follow-blue?logo=linkedin&logoColor=white&style=flat" height="20">
      </a>
      <a href="mailto:nadine.igonin@utdallas.edu" target="_blank">
        <img src="https://img.shields.io/badge/Email-Send-red?logo=gmail&logoColor=white&style=flat" height="20">
      </a>
    </td>
    <td width="100" align="center">
      <img src="https://raw.githubusercontent.com/ecastillot/UTDQuake/main/docs/source/_static/photos/nadine.jpg" alt="Nadine" width="80" height="80" style="border-radius:50%; object-fit:cover;">
    </td>
  </tr>
  <tr>
    <td valign="middle">
      <strong>Marine Denolle</strong><br>
      University of Washington<br>
      <a href="https://www.linkedin.com/in/marine-denolle-b528144b/" target="_blank">
        <img src="https://img.shields.io/badge/LinkedIn-Follow-blue?logo=linkedin&logoColor=white&style=flat" height="20">
      </a>
      <a href="mailto:mdenolle@uw.edu" target="_blank">
        <img src="https://img.shields.io/badge/Email-Send-red?logo=gmail&logoColor=white&style=flat" height="20">
      </a>
    </td>
    <td width="100" align="center">
      <img src="https://raw.githubusercontent.com/ecastillot/UTDQuake/main/docs/source/_static/photos/marine.jpg" alt="Marine" width="80" height="80" style="border-radius:50%; object-fit:cover;">
    </td>
  </tr>
</table>


