![Twitter Follow](https://img.shields.io/twitter/follow/manuavid?style=social)![GitHub followers](https://img.shields.io/github/followers/ecastillot?style=social)![GitHub stars](https://img.shields.io/github/stars/ecastillot/EQviewer?style=social)![GitHub forks](https://img.shields.io/github/forks/ecastillot/EQviewer?style=social)

# UTDQuake
University of Texas at Dallas Earthquake Dataset

# Authors
- Emmanuel Castillo (edc240000@utdallas.edu)
- Riven White (Riven.White@utdallas.edu)

# Examples

| Examples | Notebook  |
|---|---|
| UTDClient| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ecastillot/UTDQuake/blob/main/examples/utd_client.ipynb) |
|---|---|
| UTDWindow| [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ecastillot/UTDQuake/blob/main/examples/utd_window.ipynb) |

# Versions

## Development
- 0.0.17 Fixing bug detected by Riven (add_artificial_picks and remove_phases_randomly)
- 0.0.16 eda functions (riven)
- 0.0.15 pytable requirement
- 0.0.14 Window
- 0.0.13 Picks - add_artificial_picks, plot
- 0.0.11
    Fixing error: No agency
- 0.0.8 & 0.0.9:
    Fixing init bugs
- 0.0.7:
    - clients
        - utd:
            UTD module is only used to write custom earthquake dataset
            (stations.db,catalog.csv,pics.db,mag.db)
        - fdsn:
            Custom FDSN client now is part of fdsn module
    - core
        - database: Load and read dataframes from sql (chunk is included)
        - event: Different classes to manage different type of dataframes      (events,stations,picks)
    
- 0.0.6:
    - tools:
        Bug Fixed: missing __init__ file
- 0.0.5:
    Requirement: python >= 3.10
- 0.0.4: 
    - clients:
        - utd: (from FDSN): 
            - get_custom_stations: Retrieve custom station information and optionally save it to a CSV file.
- 0.0.3: 
    - clients: 
        - local: (from SDS) : Allow to upload local data from obspy easily 
        - utd: (from FDSN): 
            - get_custom_events: Retrieves custom seismic event data, including origins, picks, and magnitudes.
            - get_stats:
            Retrieve waveforms and compute rolling statistics for the specified time interval. 
                - Availability percentage
                - Gaps duration
                - Overlaps duration
                - Gaps count
                - Overlaps count
    - core:
        - database: Load and read dataframs from sql
    - scan:
        - scan: 
            - scanner:
                - scan: Scan the waveform data for each provider and save results to the database.
                - get_stats: Retrieve statistical data from database files based on the provided criteria.
            - plot_rolling_stats: Plots rolling statistics data as a heatmap with optional color bar and time axis customization.
    - tools:
        - stats:
            - get_stats_by_instrument: Calculate statistics for seismic data from specified channels and time range.
            - get_stats: Calculate statistics for seismic data grouped by instrument.
            - get_rolling_stats: Calculate rolling statistics for seismic data over specified time intervals.
