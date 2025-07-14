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
from utdquake.bank.event_bank import EventBank
from utdquake.bank.utils import load_stations_metadata_from_bank


# === CONFIG ===
bank_path = "/groups/igonin/Bank"
events_path = os.path.join(bank_path, "events")
output_dir = "/groups/igonin/ecastillo/UTDQuake/project/events/plots"
os.makedirs(output_dir, exist_ok=True)

# Optional global region
global_region = None


def compute_region(df_events, df_stations, padding=0.5, global_region=None, 
                how="events",
                force_global_if_span_gt=180):
    """
    Compute a smart bounding box. If the region is huge (global),
    then fallback to full-world view.
    """
    if global_region is not None:
        return global_region


    # Combine
    if how == "events":
        lons = df_events['longitude'].dropna().values
        lats = df_events['latitude'].dropna().values
    elif how == "stations":
        lons = df_stations['longitude'].dropna().values
        lats = df_stations['latitude'].dropna().values
    elif how == "both":
        lons = pd.concat([df_events['longitude'], df_stations['longitude']]).dropna().values
        lats = pd.concat([df_events['latitude'], df_stations['latitude']]).dropna().values
    else:
        raise ValueError(f"Unknown 'how' parameter: {how}. Use 'events', 'stations', or 'both'.")

    if len(lons) == 0 or len(lats) == 0:
        raise ValueError("No coordinates found to compute region.")

    # Convert to [0, 360)
    lons_360 = lons % 360
    lon_min_360 = lons_360.min()
    lon_max_360 = lons_360.max()
    span = lon_max_360 - lon_min_360

    # If the cluster is tight → keep it local
    if span <= force_global_if_span_gt:
        lon_min = lon_min_360
        lon_max = lon_max_360
    else:
        # Data scattered globally → fallback to full-world
        return (-180, 180, -90, 90)

    # Back to [-180, 180]
    lon_min = ((lon_min + 180) % 360) - 180
    lon_max = ((lon_max + 180) % 360) - 180

    lat_min = lats.min() - padding
    lat_max = lats.max() + padding

    if lon_min > lon_max:
        lon_min = -180

    return (lon_min, lon_max, lat_min, lat_max)

def add_scalebar(ax, region, location='upper left'):
    """
    Add a simple scale bar to a Cartopy GeoAxes.

    Parameters:
    -----------
    ax : cartopy.mpl.geoaxes.GeoAxes
        The GeoAxes to draw the scale bar on.
    region : tuple
        (lon_min, lon_max, lat_min, lat_max) map extent.
    location : str
        'upper left', 'upper right', 'lower left', 'lower right'.
    """
    lon_min, lon_max, lat_min, lat_max = region
    lon_range = lon_max - lon_min
    lat_range = lat_max - lat_min
    lat_mean = (lat_min + lat_max) / 2

    # Approx degrees longitude ≈ km at mean latitude
    lon_km = lon_range * np.cos(np.radians(lat_mean)) * 111.32

    # Choose rounded scale length
    scale_length_km = 50  # fallback
    for l in [20, 50, 100, 200, 500, 1000]:
        if lon_km / 5 > l:
            scale_length_km = l

    deg_per_km = 1 / (np.cos(np.radians(lat_mean)) * 111.32)
    scale_length_deg = scale_length_km * deg_per_km

    # Position
    x_pad = 0.05 * lon_range
    y_pad = 0.05 * lat_range

    if 'left' in location:
        x0 = lon_min + x_pad
    else:
        x0 = lon_max - x_pad - scale_length_deg

    if 'upper' in location:
        y0 = lat_max - y_pad
    else:
        y0 = lat_min + y_pad

    # Draw scale bar
    ax.plot(
        [x0, x0 + scale_length_deg],
        [y0, y0],
        transform=ax.projection,
        color='k',
        linewidth=2
    )

    ax.text(
        x0 + scale_length_deg / 2,
        y0 + y_pad * 0.3,
        f"{scale_length_km} km",
        ha='center',
        va='bottom',
        transform=ax.projection,
        fontsize=8,
        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.8)
    )

# === Single map ===
def plot_network_map(df_events, df_stations, analysis, region, ax):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cartopy
    from cartopy.mpl.geoaxes import GeoAxes
    from cartopy.geodesic import Geodesic

    import matplotlib.ticker as mticker
    from matplotlib.lines import Line2D

    ax.set_extent(region, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.STATES, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='black')
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)


    ax.scatter(
        df_stations['longitude'],
        df_stations['latitude'],
        marker='^',
        c='green',
        s=40,
        alpha=0.7,
        edgecolor='k',
        transform=ccrs.PlateCarree(),
        label='Stations'
    )
    eq = ax.scatter(
        df_events['longitude'],
        df_events['latitude'],
        color="red",
        alpha=1,
        edgecolor='k',
        transform=ccrs.PlateCarree(),
        label='Earthquakes'
    )
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
    gl.bottom_labels = False
    gl.right_labels = False
    ax.set_title(f"Contributor: {analysis['contributor']}", fontsize=10)
    add_scalebar(ax, region, location='upper left')
    
    # ax.legend(loc='lower left', fontsize='x-small')

    

    eq_lat_mean = df_events['latitude'].mean()
    eq_lon_mean = df_events['longitude'].mean()
    # === Add inset globe ===
    # === Add a simple locator map inset ===
    axins = ax.figure.add_axes(
        [0.05, 0.05, 0.25, 0.25],  # [left, bottom, width, height]
        projection=ccrs.PlateCarree()
    )

    # Set the extent to the whole world
    axins.set_global()

    # Add features
    axins.add_feature(cfeature.LAND, facecolor='lightgray')
    axins.add_feature(cfeature.OCEAN, facecolor='lightblue')
    axins.add_feature(cfeature.COASTLINE, linewidth=0.5)
    axins.add_feature(cfeature.BORDERS, linestyle=':')

    axins.scatter(
        df_stations['longitude'],
        df_stations['latitude'],
        marker='^',
        c='green',
        s=20,
        alpha=0.7,
        edgecolor='k',
        transform=ccrs.PlateCarree(),
        label='Stations'
    )

    axins.text(
            1.2, 0.05,
            f"Events: {analysis['events_total']}\n"
            f"Good Stations: {analysis['stations_good']}\n"
            f"Bad Stations: {analysis['stations_bad']}\n"
            f"P Arrivals: {analysis['p_arrivals_total']}\n"
            f"S Arrivals: {analysis['s_arrivals_total']}",
            transform=axins.transAxes,
            ha='left',  # horizontal alignment right
            va='bottom',    # vertical alignment bottom
            fontsize=8,  # optional: make it smaller if needed
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)  # optional: add a box
            )

    lon_min, lon_max, lat_min, lat_max = region
    # Draw your region box
    rect = Rectangle(
        (lon_min, lat_min),
        lon_max - lon_min,
        lat_max - lat_min,
        linewidth=1.5,
        edgecolor='red',
        facecolor='none',
        transform=ccrs.PlateCarree()
    )
    axins.add_patch(rect)


    return eq


# === Contributors ===
contributors = sorted(glob.glob(os.path.join(events_path, "*")))
# contributors = [ 
#                     'ci', 
#                     'se',
#                      'tx',
#                      'ak', 'nn',  'pr', 'us'
#                     ]
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
        base_path=path,
        path_structure='{year}/{month}/{day}/{hour}',
        name_structure='{event_id_end}',
        format='quakeml'
    )

    events = ebank.get_event_summary()

    cat = ebank.get_events(event_id=events.event_id.values)
    summary = ebank.get_summary()
    specific_summary = summary.iloc[:,4::]
    analysis = specific_summary.sum(axis=0).to_dict()
    gd_stations = ebank.get_station_summary(available=True)
    bd_stations = ebank.get_station_summary(available=False)

    analysis['contributor'] = contributor

    # Save for global
    all_events.append(events[['time','longitude', 'latitude', 'magnitude']])
    
    if gd_stations.empty:
        print(f"❌ No  stations for {contributor}")
        continue
    else:
        all_stations.append(gd_stations[['network','station','longitude', 'latitude']])

    # continue
    region = compute_region(
        events, gd_stations, padding=0.5, 
        global_region=global_region)
    print("region",region)

    # === Plot ===
    fig = plt.figure(figsize=(12, 6), dpi=300)

    # Map
    ax_map = plt.subplot2grid((2, 3), (0, 0), rowspan=2, 
                    colspan=2, projection=ccrs.PlateCarree())
    eq = plot_network_map(events, gd_stations, analysis, 
                    region, ax_map)

    # Depth histogram (top right)
    ax_depth = plt.subplot2grid((2, 3), (0, 2))
    if 'depth' in events.columns:
        ax_depth.hist(events['depth'].dropna()/1e3, bins=20, color='gray', edgecolor='black')
        ax_depth.set_xlabel("Depth (km)")
        ax_depth.set_ylabel("Count")
        ax_depth.set_title("Depth Histogram")
    else:
        ax_depth.set_title("No Depth Data")
        ax_depth.axis('off')

    # Magnitude histogram (bottom right)
    ax_mag = plt.subplot2grid((2, 3), (1, 2))
    ax_mag.hist(events['magnitude'].dropna(), bins=20, color='orange', edgecolor='black')
    ax_mag.set_xlabel("Magnitude")
    ax_mag.set_ylabel("Count")
    ax_mag.set_title("Magnitude Histogram")

    fig.tight_layout()
    out_path = os.path.join(output_dir, f"{contributor}.png")
    fig.savefig(out_path, dpi=300)
    print(f"✅ Saved: {out_path}")
    plt.close(fig)

# === Final global overview ===


df_all_events = pd.concat(all_events, ignore_index=True)
df_all_stations = pd.concat(all_stations, ignore_index=True).drop_duplicates()

if global_region is None:
    lon_min = min(df_all_events['longitude'].min(), df_all_stations['longitude'].min()) - 1
    lon_max = max(df_all_events['longitude'].max(), df_all_stations['longitude'].max()) + 1
    lat_min = min(df_all_events['latitude'].min(), df_all_stations['latitude'].min()) - 1
    lat_max = max(df_all_events['latitude'].max(), df_all_stations['latitude'].max()) + 1
    region = (lon_min, lon_max, lat_min, lat_max)
else:
    region = global_region

fig = plt.figure(figsize=(12, 12), dpi=300)
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent(region, crs=ccrs.PlateCarree())

ax.add_feature(cfeature.COASTLINE)
ax.add_feature(cfeature.BORDERS, linestyle=':')
ax.add_feature(cfeature.STATES, linestyle=':')
ax.add_feature(cfeature.LAND, edgecolor='black')
ax.add_feature(cfeature.OCEAN)
ax.add_feature(cfeature.LAKES, alpha=0.5)
ax.add_feature(cfeature.RIVERS)

ax.scatter(
    df_all_stations['longitude'],
    df_all_stations['latitude'],
    marker='^',
    c='green',
    s=40,
    # alpha=0.7,
    edgecolor='k',
    transform=ccrs.PlateCarree(),
    label='Stations'
)
eq = ax.scatter(
    df_all_events['longitude'],
    df_all_events['latitude'],
    alpha=0.5,
    color="red",
    edgecolor='k',
    transform=ccrs.PlateCarree(),
    label='Earthquakes'
)


ax.set_title("Global Overview: All Earthquakes & Stations", 
            fontsize=16)

overview_outfile = os.path.join(output_dir, "global_overview.png")
fig.savefig(overview_outfile, dpi=300)
print(f"✅ Saved: {overview_outfile}")
plt.close(fig)
