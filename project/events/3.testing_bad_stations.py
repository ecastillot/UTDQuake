import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import os
import glob
import pandas as pd
import obsplus
from matplotlib.patches import Rectangle
from utdquake.bank.utils import load_stations_metadata_from_bank
import matplotlib.pyplot as plt

# === CONFIG ===
bank_path = "/groups/igonin/PHASED"
events_path = os.path.join(bank_path, "events")
stations_path = os.path.join(bank_path, "stations", ".stations.db")
output_dir = "/groups/igonin/ecastillo/UTDQuake/project/events/plots"
os.makedirs(output_dir, exist_ok=True)

stations_metadata = load_stations_metadata_from_bank(stations_path)
stations_metadata = stations_metadata.drop_duplicates(subset=['network', 'station','longitude','latitude'])

# === Contributors ===
contributors = sorted(glob.glob(os.path.join(events_path, "*")))
# contributors = ["ak"]
for path in contributors:
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    contributor = os.path.basename(path)

    if contributor not in ["ak"]:
        continue

    ebank = obsplus.EventBank(
        base_path=path,
        path_structure='{year}/{month}/{day}/{hour}',
        name_structure='{event_id_end}',
        format='quakeml'
    )

    df_index = ebank.read_index()
    df_index['contributor'] = contributor

    cat = ebank.get_events(event_id=df_index.event_id.values)
    arrivals = cat.arrivals_to_df()
    arrival_stations = arrivals[['network', 'station']].drop_duplicates()
    
    arrival_stations = arrival_stations.merge(
        stations_metadata, on=['network', 'station'], how='left'
    )
    arrival_stations = arrival_stations.drop_duplicates(subset=['network', 'station','longitude','latitude'])

    print(arrival_stations)

    print("events", df_index.describe())
    print("arrival_stations",arrival_stations.describe())

    bad_stations = arrival_stations[['latitude', 'longitude']].isna().any(axis=1)
    
    print("Bad stations:", arrival_stations[bad_stations])
    print(bad_stations.sum(), "stations without metadata")
    
    arrival_stations.dropna(inplace=True)
    print(len(arrival_stations), "stations with metadata")
    # for i,row in arrival_stations.iterrows():
    #     print(row.network,row.station,row.latitude,row.longitude)
    # for i,row in df_index.iterrows():
    #     print(row.latitude,row.longitude)
        
    plt.figure(figsize=(10, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())    
    ax.plot(
        df_index.longitude.values, df_index.latitude.values,label='Events',
        marker='o', markersize=5, color='red', linestyle='None', transform=ccrs.PlateCarree()
    )
    ax.plot(
        arrival_stations.longitude.values, arrival_stations.latitude.values, label='Stations',
        marker='^', markersize=5, color='blue', linestyle='None', transform=ccrs.PlateCarree()
    )

    plt.savefig(os.path.join(output_dir, f"{contributor}_events_stations.png"), dpi=300)