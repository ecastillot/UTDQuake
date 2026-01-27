import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import os
import glob
import numpy as np
import pandas as pd
import obsplus
from matplotlib.patches import Rectangle

from utdquake.bank.bank import EventBank
#from utdquake.bank.utils import load_stations_metadata_from_bank
from utdquake.plot.utils import plot_network_map,human_format,plot_network_map_stats

# === CONFIG ===
bank_path = "/groups/igonin/ecastillo/UTDBank/bank"
events_path = bank_path
output_dir = "/groups/igonin/ecastillo/UTDQuake/test/10132025/plots"
os.makedirs(output_dir, exist_ok=True)

# Optional global region
global_region = None


def compute_region(
    df_events,
    df_stations,
    padding=0.2,
    global_region=None,
    how="events",
    rm_outliers=False,
    force_global_if_span_gt=180
    ):
    """
    Compute a smart bounding box for plotting events/stations.
    Handles wrap-around at the dateline.
    
    Parameters:
        df_events: pd.DataFrame with 'longitude' and 'latitude'
        df_stations: pd.DataFrame with 'longitude' and 'latitude'
        padding: float, fraction of span to pad
        global_region: if given, use this instead
        how: 'events', 'stations', or 'both'
        rm_outliers: bool, remove extreme outliers
        force_global_if_span_gt: if lon span > this, fallback to world view
    
    Returns:
        (lon_min, lon_max, lat_min, lat_max)
        Note: lon_min may be greater than lon_max if region wraps around dateline
    """

    if global_region is not None:
        return global_region

    # --- Collect data ---
    if how == "events":
        lons = df_events['longitude'].dropna()
        lats = df_events['latitude'].dropna()
    elif how == "stations":
        lons = df_stations['longitude'].dropna()
        lats = df_stations['latitude'].dropna()
    elif how == "both":
        lons = pd.concat([df_events['longitude'], df_stations['longitude']]).dropna()
        lats = pd.concat([df_events['latitude'], df_stations['latitude']]).dropna()
    else:
        raise ValueError(f"Unknown how='{how}'. Must be 'events', 'stations', or 'both'.")

    if lons.empty or lats.empty:
        raise ValueError("No valid coordinates to compute region.")

    # --- Remove outliers ---
    if rm_outliers:
        lons_mean, lons_std = lons.mean(), lons.std()
        lats_mean, lats_std = lats.mean(), lats.std()
        lons = lons[(lons >= lons_mean - 6 * lons_std) & (lons <= lons_mean + 6 * lons_std)]
        lats = lats[(lats >= lats_mean - 6 * lats_std) & (lats <= lats_mean + 6 * lats_std)]

    lons = lons.values
    lats = lats.values

    # --- Compute latitude bounds ---
    lat_min, lat_max = np.min(lats), np.max(lats)
    lon_min, lon_max = np.min(lons), np.max(lons)

    #padding
    lon_distance = lon_max - lon_min
    lat_distance = lat_max - lat_min
    lon_min -= padding * lon_distance
    lon_max += padding * lon_distance
    lat_min -= padding * lat_distance
    lat_max += padding * lat_distance

    if lon_min < -180:
        lon_min=-180
    if lon_max > 180:
        lon_max=180
    if lat_min < -90:
        lat_min=-90
    if lat_max > 90:
        lat_max=90

    return (lon_min, lon_max, lat_min, lat_max)

    
# === Single map ===
max_n_events = 10
# # === Contributors ===
contributors = sorted(glob.glob(os.path.join(events_path, "*")))

# contributors = [ 
#                 #   'av', 'ak'
#                 #    'IGIL'
#                    'WEL','INMG'
#                 #   'tx'
#                     ]
# contributors = ["av"]
alaska = True if "av" in contributors or "ak" in contributors else False
# contributors = ["JAPAN"]
# contributors = ["VAO"]
contributors = [os.path.join(events_path, c) for c in contributors]

# === Accumulate for final overview ===
all_events = []
all_stations = []

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

for path in contributors:

    contributor = os.path.basename(path)

    print(f"Contributor: {contributor} with path: {path}")

    ebank = EventBank(
        path,
        path_structure='{year}/{month}/{day}/{hour}',
        name_structure='{event_id_end}',
        format='quakeml'
    )



    # picks = ebank.get_picks_summary()
    # calculated_picks = picks[picks["index"]=="calculated_stations"]
    # confirmed_stations = ebank.get_stations("confirmed")
    # calculated_stations = ebank.get_stations("calculated")
    # missing_stations = ebank.get_stations("missing")

    # print(missing_stations)
    # print(ebank.get_table_names())
    try:
        stations = ebank.get_stations()
    except:
        print(f"❌ No stations for {contributor}")
        continue
    stations.drop_duplicates(subset=["network","station"], inplace=True)
    n_total_stations = len(stations)
    confirmed_stations = stations[stations["confirmed"]==True]
    calculated_stations = stations[stations["calculated"]==True]

    n_confirmed_stations = len(confirmed_stations)
    n_calculated_stations = len(calculated_stations)
    # print(stations.info())
    # exit()
    
    
    events = ebank.read_index()
    events = events.dropna(subset=["latitude","longitude"])

    # print(events[["p_phase_count","s_phase_count"]].describe())
    n_p_picks = events['p_phase_count'].sum()
    n_s_picks = events['s_phase_count'].sum()

    # print(events.info())
    # exit()

    print("plotting",len(events))
    if len(events) == 0 or events.empty:
        continue

    if len(events) < max_n_events:
        continue
    # print("plotting",len(events))

    # cat = ebank.get_events(event_id=events.event_id.values)
    # try:
        # summary = ebank.get_summary()
    # except:
        # print("No possible",contributor)
    # specific_summary = summary.iloc[:,4::]
    # analysis = specific_summary.sum(axis=0).to_dict()
    # gd_stations = ebank.get_station_summary(available=True)
    # bd_stations = ebank.get_station_summary(available=False)

    # analysis['stations_good'] = len(gd_stations)
    # analysis['stations_bad'] = len(bd_stations)


    analysis = {
            "Events": len(events),
            "Total Stations": n_total_stations,
            "Calculated Stations": n_calculated_stations,
            "Confirmed Stations": n_confirmed_stations,
            "P arrivals": n_p_picks,
            "S arrivals": n_s_picks,
    }

    analysis['contributor'] = contributor

    all_events.append(events)

    gd_stations = calculated_stations.rename(columns={"calculated_longitude": "longitude",
                                                "calculated_latitude": "latitude",
                                                "calculated_elevation": "elevation"})
    if gd_stations.empty:
        print(f"❌ No  stations for {contributor}")
        continue

    region = compute_region(
        events, gd_stations, padding=0.2, 
        global_region=global_region,
        rm_outliers=True)
    print("region",region)


    # === Plot ===
    fig = plt.figure(figsize=(12, 6), dpi=300)

    # Map
    out_path = os.path.join(output_dir, f"{contributor}.png")                
    eq = plot_network_map_stats(events=events, stations=gd_stations,
                        region=region, analysis=analysis,
                        output_file=out_path,
                        alaska=alaska)

    

    if stations.empty:
        print(f"❌ No  stations for {contributor}")
        continue
    else:
        all_stations.append(stations)

# exit()
# === Final global overview ===


df_all_events = pd.concat(all_events, ignore_index=True)
df_all_stations = pd.concat(all_stations, ignore_index=True).drop_duplicates()

out_events = os.path.join(output_dir, "all_events.csv")
df_all_events.to_csv(out_events, index=False)
out_stations = os.path.join(output_dir, "all_stations.csv")
df_all_stations.to_csv(out_stations, index=False)
print(f"✅ Saved: {out_events}")


n_p_picks = df_all_events['p_phase_count'].sum()
n_s_picks = df_all_events['s_phase_count'].sum()

df_all_stations.drop_duplicates(subset=["network","station"], inplace=True)
n_total_stations = len(df_all_stations)
confirmed_stations = df_all_stations[df_all_stations["confirmed"]==True]
calculated_stations = df_all_stations[df_all_stations["calculated"]==True]

n_confirmed_stations = len(confirmed_stations)
n_calculated_stations = len(calculated_stations)


analysis = {
            "Events": len(df_all_events),
            "Total Stations": n_total_stations,
            "Calculated Stations": n_calculated_stations,
            "Confirmed Stations": n_confirmed_stations,
            "P arrivals": n_p_picks,
            "S arrivals": n_s_picks,
    }

# if global_region is None:
#     lon_min = min(df_all_events['longitude'].min(), df_all_stations['longitude'].min()) - 1
#     lon_max = max(df_all_events['longitude'].max(), df_all_stations['longitude'].max()) + 1
#     lat_min = min(df_all_events['latitude'].min(), df_all_stations['latitude'].min()) - 1
#     lat_max = max(df_all_events['latitude'].max(), df_all_stations['latitude'].max()) + 1
#     region = (lon_min, lon_max, lat_min, lat_max)
# else:
    # region = global_region

def setup_map(ax, region):
    ax.set_extent(region, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.STATES, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='black')
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)

    # Gridlines (labels on bottom/right)
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                      alpha=0.7, linestyle='--')
    gl.top_labels = True
    gl.left_labels = True  # right side labels instead
    gl.right_labels = False
    gl.bottom_labels = True

    return ax,gl

region = (-180, 180, -90, 90) if global_region is None else global_region

# Create figure with shared X-axis
fig, (ax1, ax2) = plt.subplots(
    nrows=2, ncols=1,
    figsize=(12, 8), dpi=300,
    subplot_kw={'projection': ccrs.PlateCarree()},
    sharex=True
)

# ---- Earthquakes (top subplot) ----
ax1,gl1 = setup_map(ax1, region)
gl1.top_labels = True
gl1.right_labels = False
gl1.left_labels = True  # right side labels instead
gl1.bottom_labels = False
ax1.scatter(
    df_all_events['longitude'],
    df_all_events['latitude'],
    # alpha=0.5, 
    # color="red",
    color="#ec7524",
    transform=ccrs.PlateCarree(),
    label='Earthquakes'
)
ax1.legend(loc='lower right', fontsize=12)

ax1.text(
    0.02, 0.05,  # bottom-left
    f"Events: {human_format(analysis.get('Events', len(events)))}\n"
    f"P Arrivals: {human_format(analysis.get('P arrivals', 0))}\n"
    f"S Arrivals: {human_format(analysis.get('S arrivals', 0))}",
    transform=ax1.transAxes,
    ha='left',
    va='bottom',
    fontsize=12,
    bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
)

# ---- Stations (bottom subplot) ----
ax2,gl2 = setup_map(ax2, region)
gl2.top_labels = False
gl2.right_labels = False
gl2.left_labels = True  # right side labels instead
gl2.bottom_labels = True
ax2.scatter(
    calculated_stations['calculated_longitude'],
    calculated_stations['calculated_latitude'],
    marker='^', c='green', s=40,
    alpha=0.7, transform=ccrs.PlateCarree(),
    label='Stations'
)
ax2.legend(loc='lower right', fontsize=12)

ax2.text(
    0.02, 0.05,  # bottom-left
    f"Total Stations: {human_format(analysis['Total Stations'])}\n"
    f"   Calculated: {human_format(analysis['Calculated Stations'])}\n"
    f"   Confirmed: {human_format(analysis['Confirmed Stations'])}",
    transform=ax2.transAxes,
    ha='left',
    va='bottom',
    fontsize=12,
    bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
)

# plt.tight_layout()
plt.subplots_adjust(hspace=0.05)
overview_outfile = os.path.join(output_dir, "earthquakes_stations_overview.png")
plt.savefig(overview_outfile, dpi=300)
plt.close(fig)

print(f"✅ Saved: {overview_outfile}")
