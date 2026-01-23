
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Follow-blue?logo=linkedin)](https://www.linkedin.com/in/ecastillot/) ![GitHub followers](https://img.shields.io/github/followers/ecastillot?style=social)  ![GitHub stars](https://img.shields.io/github/stars/ecastillot/UTDQuake?style=social) ![GitHub forks](https://img.shields.io/github/forks/ecastillot/UTDQuake?style=social)



# <span style="background:#E87500; color:white; padding:2px 6px; border-radius:6px;">UTD</span>Quake

University of Texas at Dallas Earthquake Dataset

# Authors
- Emmanuel Castillo (edc240000@utdallas.edu)
- Nadine Ushakov
- Marine Denolle

# Dataset

The dataset is available on Hugging Face: **UTDQuake**  

[![Hugging Face Dataset](https://img.shields.io/badge/HuggingFace-Dataset-yellow?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/datasets/ecastillot/UTDQuake)

## What’s inside?

- `events/` → zipped datasets per network (`*.zip`)
- Each network contains event and pick information (when available)

## Quick start

### Access
```python
import utdquake as utdq

# loads tx
bank =  utdq.load_network("tx")   
print(bank.stats)

# read events information
df = bank.read_index()    
print(df.head())

ev_ids = df["event_id"].tolist()[:5]
picks = bank.get_picks(event_ids=ev_ids)
print(picks)
```

### Catalog
```python
# get Obspy Catalog
catalog = bank.get_events(starttime=UTCDateTime("2025-07-31T00:00:00"), 
                            endtime=UTCDateTime("2025-07-31T12:00:00"))
print(catalog)
print(catalog.to_df())

# get Obspy Event
event = catalog[0]
picks = event.picks_to_df()
arrivals = event.arrivals_to_df()
print(event,picks,arrivals)
```

### Picks db (Massive)
```python
# Save
bank.save_picks()
picks = bank.load_picks()
print(picks)
```

### Plot
```python
# get Obspy Event
bank.plot_overview("./overview.png")
bank.plot_uncertainty_boxplots("./uncertainty_boxplots.png")
bank.plot_station_location_uncertainty("./station_location_uncertainty.png")
bank.plot_stats("./stats.png")
bank.plot_histograms("./histograms.png")
bank.plot_pick_stats("./pick_stats.png")
```


