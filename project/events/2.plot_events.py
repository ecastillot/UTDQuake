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

# === CONFIG ===
bank_path = "/groups/igonin/PHASED"
events_path = os.path.join(bank_path, "events")
stations_path = os.path.join(bank_path, "stations", ".stations.db")
output_dir = "/groups/igonin/ecastillo/UTDQuake/project/events/plots"
os.makedirs(output_dir, exist_ok=True)

stations_metadata = load_stations_metadata_from_bank(stations_path)
stations_metadata = stations_metadata.drop_duplicates(subset=['network', 'station','location'])

# Optional global region
global_region = None


def compute_region(df_events, df_stations, padding=0.5, global_region=None, force_global_if_span_gt=180):
    """
    Compute a smart bounding box. If the region is huge (global),
    then fallback to full-world view.
    """
    if global_region is not None:
        return global_region

    # Combine
    lons = pd.concat([df_events['longitude'], df_stations['longitude']]).dropna().values
    lats = pd.concat([df_events['latitude'], df_stations['latitude']]).dropna().values

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

    return (lon_min, lon_max, lat_min, lat_max)

# === Single map ===
def plot_network_map(df_events, df_stations, contributor, region, ax):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cartopy
    from cartopy.mpl.geoaxes import GeoAxes

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
    ax.set_title(f"{contributor}", fontsize=10)
    ax.legend(loc='lower left', fontsize='x-small')



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

# === Accumulate for final overview ===
all_events = []
all_stations = []

for path in contributors:
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    contributor = os.path.basename(path)

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
    arrival_stations = arrivals[['network', 'station','location']].drop_duplicates()
    arrival_stations = arrival_stations.merge(
        stations_metadata, on=['network', 'station','location'], how='left'
    )
    print("events", df_index.describe())
    print("arrival_stations",arrival_stations.describe())


    # Save for global
    all_events.append(df_index[['longitude', 'latitude', 'magnitude']])
    all_stations.append(arrival_stations[['longitude', 'latitude']])

    # Region
    if contributor in ["ak","av"]:
        # Special case for Alaska, use a global region
        # global_region = (178, -178, -90, 90)
        region = (-179.9,-115, 0, 90)
    else:
        region = compute_region(
            df_index, arrival_stations, padding=0.5, global_region=global_region)
    print("region",region)

    # === Plot ===
    fig = plt.figure(figsize=(12, 6), dpi=300)

    # Map
    ax_map = plt.subplot2grid((2, 3), (0, 0), rowspan=2, colspan=2, projection=ccrs.PlateCarree())
    eq = plot_network_map(df_index, arrival_stations, contributor, region, ax_map)

    # Depth histogram (top right)
    ax_depth = plt.subplot2grid((2, 3), (0, 2))
    if 'depth' in df_index.columns:
        ax_depth.hist(df_index['depth'].dropna()/1e3, bins=20, color='gray', edgecolor='black')
        ax_depth.set_xlabel("Depth (km)")
        ax_depth.set_ylabel("Count")
        ax_depth.set_title("Depth Histogram")
    else:
        ax_depth.set_title("No Depth Data")
        ax_depth.axis('off')

    # Magnitude histogram (bottom right)
    ax_mag = plt.subplot2grid((2, 3), (1, 2))
    ax_mag.hist(df_index['magnitude'].dropna(), bins=20, color='orange', edgecolor='black')
    ax_mag.set_xlabel("Magnitude")
    ax_mag.set_ylabel("Count")
    ax_mag.set_title("Magnitude Histogram")

    fig.tight_layout()
    out_path = os.path.join(output_dir, f"{contributor}.png")
    fig.savefig(out_path, dpi=300)
    print(f"✅ Saved: {out_path}")
    plt.close(fig)

# === Final global overview ===
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

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

eq = ax.scatter(
    df_all_events['longitude'],
    df_all_events['latitude'],
    c=df_all_events['magnitude'],
    s=df_all_events['magnitude'] ** 2 * 5,
    cmap='hot_r',
    alpha=0.5,
    edgecolor='k',
    transform=ccrs.PlateCarree(),
    label='Earthquakes'
)

ax.scatter(
    df_all_stations['longitude'],
    df_all_stations['latitude'],
    marker='^',
    c='blue',
    s=40,
    edgecolor='k',
    transform=ccrs.PlateCarree(),
    label='Stations'
)

plt.colorbar(eq, ax=ax, orientation='vertical', label='Magnitude')
ax.legend(loc='lower left')
ax.set_title("Global Overview: All Earthquakes & Stations", fontsize=16)

overview_outfile = os.path.join(output_dir, "global_overview.png")
fig.savefig(overview_outfile, dpi=300)
print(f"✅ Saved: {overview_outfile}")
plt.close(fig)
