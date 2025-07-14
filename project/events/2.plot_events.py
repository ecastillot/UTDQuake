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
from utdquake.bank.utils import load_stations_metadata_from_bank


# === CONFIG ===
bank_path = "/groups/igonin/Bank"
events_path = os.path.join(bank_path, "events")
stations_path = os.path.join(bank_path, "stations", ".stations.db")
output_dir = "/groups/igonin/ecastillo/UTDQuake/project/events/plots"
os.makedirs(output_dir, exist_ok=True)

stations_metadata = load_stations_metadata_from_bank(stations_path)


# Optional global region
global_region = None

def merge_arrivals_and_picks(
    arrivals: pd.DataFrame,
    picks: pd.DataFrame,
    picks_subset_columns: list = ['time']
) -> pd.DataFrame:
    """
    Merge arrivals with a subset of columns from picks, using 'seed_id'.
    Keeps all arrival columns plus the specified columns from picks.

    :param arrivals: DataFrame with arrival info.
    :param picks: DataFrame with pick info.
    :param picks_subset_columns: List of column names from picks to keep (default is ['time']).
    :return: Merged DataFrame.
    """
    # Always include 'resource_id' for the join
    picks_subset = picks[['resource_id'] + picks_subset_columns]

    merged = pd.merge(
                arrivals,
                picks_subset,
                left_on='pick_id',     # column in arrivals
                right_on='resource_id', # column in picks
                how='inner'             # or 'left', 'right', 'outer'
            )
    return merged

def standardize_phases(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each network-station pair, keep only one P and one S.
    Rename Pg, Pn, etc. to P if no explicit P exists.
    Pick the earliest arrival for each.
    """
    # Identify P-type and S-type phases
    P_phases = ['P', 'Pg', 'Pn', 'Pb']
    S_phases = ['S', 'Sn', 'Sg']

    def keep_first_P_S(group):
        # Filter for P-type and S-type
        p_group = group[group['phase'].isin(P_phases)]
        s_group = group[group['phase'].isin(S_phases)]

        selected = []

        # Handle P
        if not p_group.empty:
            # If explicit P exists, keep only it
            if 'P' in p_group['phase'].values:
                p_group = p_group[p_group['phase'] == 'P']
            # Take earliest by time
            first_p = p_group.loc[p_group['time'].idxmin()]
            first_p = first_p.copy()
            first_p['phase'] = 'P'
            selected.append(first_p)

        # Handle S
        if not s_group.empty:
            if 'S' in s_group['phase'].values:
                s_group = s_group[s_group['phase'] == 'S']
            first_s = s_group.loc[s_group['time'].idxmin()]
            first_s = first_s.copy()
            first_s['phase'] = 'S'
            selected.append(first_s)

        return pd.DataFrame(selected)

    cleaned = df.groupby(['origin_id','network', 'station'], group_keys=False).apply(keep_first_P_S)

    return cleaned.reset_index(drop=True)

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
            f"Events: {analysis['events']['total']}\n"
            f"Good Stations: {analysis['stations']['good']}\n"
            f"Bad Stations: {analysis['stations']['bad']}\n"
            f"P Arrivals: {analysis['p_arrivals']['total']}\n"
            f"S Arrivals: {analysis['s_arrivals']['total']}",
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

def parse_catalog(catalog,stations,debug=False):

    total_events = len(catalog.events)

    arrivals = catalog.arrivals_to_df()
    # test_arrivals = arrivals.copy()
    picks = catalog.picks_to_df()
    if debug:
        print("Catalog events:", total_events)
        print("Arrivals shape:", arrivals.shape)
        print("Picks shape:", picks.shape)

    # removing duplicates based on 'seed_id'
    arrivals = arrivals.drop_duplicates(subset=['resource_id'])
    picks = picks.drop_duplicates(subset=['resource_id'])

    # print(arrivals.columns)
    # print(picks.columns)
    # print("arrivals after drop duplicates by 'resource_id'", len(arrivals))

    stations = stations.drop_duplicates(subset=['network', 'station'],
                                            ignore_index=True)

    if debug:
        print("After drop duplicates arrivals by 'seed_id'", len(arrivals))
        print("After drop duplicates picks by 'seed_id'", len(picks))

    # merge arrivals with picks to extract time
    arrivals = merge_arrivals_and_picks(arrivals, picks)

    print("After merge arrivals with picks", len(arrivals))

    if debug:
        print("After merge arrivals with picks (extracting time)", len(arrivals))
        print("initial P arrivals", arrivals[arrivals['phase'].isin(['P'])].shape[0])
        print("initial S arrivals", arrivals[arrivals['phase'].isin(['S'])].shape[0])
        print("initial other arrivals", arrivals[~arrivals['phase'].isin(['P', 'S'])].shape[0])

    # standardize phases
    # This will keep only one P and one S for each network-station pair
    arrivals = standardize_phases(arrivals)

    if debug:
        print("After standardize phases arrivals", len(arrivals))
        print("P arrivals", arrivals[arrivals['phase'].isin(['P'])].shape[0])
        print("S arrivals", arrivals[arrivals['phase'].isin(['S'])].shape[0])
        print("Other arrivals", arrivals[~arrivals['phase'].isin(['P', 'S'])].shape[0])

    # arrival analysis
    total_arrivals = len(arrivals)

    total_p_arrivals = len(arrivals[arrivals['phase'].isin( ['P'])])
    total_s_arrivals = len(arrivals[arrivals['phase'].isin(['S'])])

    # print(stations.columns)
    # print(arrivals.columns)
    # print(stations[['network', 'station', 'location', 'channel','seed_id','latitude','longitude']].head(10))
    # print(arrivals[['network', 'station', 'location', 'channel','seed_id']].head(10))
    arrivals_with_stations = arrivals.merge(
                                            stations[['network', 'station','latitude', 'longitude','elevation']],
                                            on=['network', 'station'], 
                                            how='left')

    if debug:
        print("After merge arrivals with stations", len(arrivals_with_stations))
        print("P arrivals with stations", arrivals_with_stations[arrivals_with_stations['phase'].isin(['P'])].shape[0])
        print("S arrivals with stations", arrivals_with_stations[arrivals_with_stations['phase'].isin(['S'])].shape[0])
        print("Other arrivals with stations", arrivals_with_stations[~arrivals_with_stations['phase'].isin(['P', 'S'])].shape[0])
    
    gd_arrivals_mask = arrivals_with_stations[['latitude', 'longitude']].notna().all(axis=1)
    gd_arrivals = arrivals_with_stations[gd_arrivals_mask]
    total_gd_arrivals = len(gd_arrivals)
    total_p_gd_arrivals = len(gd_arrivals[gd_arrivals['phase'].isin(['P'])])
    total_s_gd_arrivals = len(gd_arrivals[gd_arrivals['phase'].isin(['S'])])

    total_bad_arrivals = total_arrivals - total_gd_arrivals
    total_bad_p_arrivals = total_p_arrivals - total_p_gd_arrivals
    total_bad_s_arrivals = total_s_arrivals - total_s_gd_arrivals


    stations_with_arrivals = arrivals_with_stations.drop_duplicates(subset=['network', 'station'])
    total_stations = len(stations_with_arrivals)
    bad_stations_mask = stations_with_arrivals[['latitude', 'longitude']].isna().any(axis=1)
    bad_stations = stations_with_arrivals[bad_stations_mask]
    gd_stations = stations_with_arrivals[~bad_stations_mask]
    total_bad_stations = len(bad_stations)
    total_gd_stations = len(gd_stations)

    analysis = {}
    analysis['events'] = {"total": total_events}
    analysis['arrivals'] = {
        "total": total_arrivals,
        "good": total_gd_arrivals,
        "bad": total_bad_arrivals}
    analysis['p_arrivals'] = {
        "total": total_p_arrivals, 
        "good": total_p_gd_arrivals,
        "bad": total_bad_p_arrivals}
    analysis['s_arrivals'] = {
        "total": total_s_arrivals,
        "good": total_s_gd_arrivals,
        "bad": total_bad_s_arrivals}
    analysis['stations'] = {
        "total": total_stations,
        "good": total_gd_stations,
        "bad": total_bad_stations}
    analysis['stations_data'] = {
        "good": gd_stations,
        "bad": bad_stations
        }


    # test = analysis["stations_data"]["good"].drop_duplicates(subset=['network', 'station'])

    # # test_stations = test_arrivals[test_arrivals[["network", "station"]].apply(tuple, axis=1).isin(test[["network", "station"]].apply(tuple, axis=1))]
    # test_stations = test_arrivals[test_arrivals[["network", "station"]].apply(tuple, axis=1).isin([("GO","SHNK"),("AU","MTN")])]
    # # print(test_stations[['network', 'station']].head(10))

    # print(f"testing arrivals with stations: IM GO AU")
    # print(test_stations)
    # print(test_arrivals[test_arrivals["network"].isin(["IM","GO","AU"])])

    # fig = plt.figure(figsize=(10, 8))
    # ax = fig.add_subplot()

    # # Basic scatter plot
    # ax.scatter(test['longitude'], test['latitude'], color='red', s=50, marker='^')

    # # Add labels (NO transform needed!)
    # for _, row in test.iterrows():
    #     ax.text(row['longitude'] + 0.05, row['latitude'] + 0.05, row["network"] +"."+ row['station'], fontsize=9)

    # ax.set_xlabel("Longitude")
    # ax.set_ylabel("Latitude")
    # ax.set_title("Station Map")

    # fig.savefig(os.path.join(output_dir, "stations_map.png"), dpi=300)
    # print("plotted")
    # print(arrivals_with_stations[['network', 'station', 'latitude', 'longitude']].head(10))


    return analysis


    # arrivals_with_stations = arrivals[['network', 'station']].drop_duplicates(ignore_index=True)

    # gd_arrivals = arrivals_with_stations.dropna(ignore_index=True)
    # fs_a


    

# === Contributors ===
contributors = sorted(glob.glob(os.path.join(events_path, "*")))
# contributors = [
#     "/groups/igonin/Bank/events/pt",
# ]

# === Accumulate for final overview ===
all_events = []
all_stations = []

for path in contributors:
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    contributor = os.path.basename(path)

    # if contributor not in ["ak"]:
    #     continue

    ebank = obsplus.EventBank(
        base_path=path,
        path_structure='{year}/{month}/{day}/{hour}',
        name_structure='{event_id_end}',
        format='quakeml'
    )

    print(path)
    xml_files = glob.glob(os.path.join(path, "**","*.xml"),recursive=True)
    xml_event_ids = [os.path.basename(f).split('.')[0] for f in xml_files]
    len_xml_files = len(xml_files)
    print(f"Found {len_xml_files} XML files in {path}")

    if len_xml_files == 0:
        print(f"Warning: No XML files found in {path}. Skipping this contributor.")
        continue

    events = ebank.read_index()
    event_xml_files = events["path"]
    xml_event_ids_in_bank = event_xml_files.apply(lambda x: os.path.basename(x).split('.')[0])

    if len_xml_files != len(xml_event_ids_in_bank):
        print(f"Warning: {len_xml_files} XML files found, but {len(xml_event_ids_in_bank)} events in the bank index.")
        print("This might indicate some files are not indexed correctly or some events are missing.")

        #check for missing events
        left_missing_events = set(xml_event_ids) - set(xml_event_ids_in_bank)
        if left_missing_events:
            print(f"Missing events in the bank index: {left_missing_events}")
        
        right_missing_events = set(xml_event_ids_in_bank) - set(xml_event_ids)
        if right_missing_events:
            print(f"Extra events in the bank index not found in XML files: {right_missing_events}")

            
    events['contributor'] = contributor

    cat = ebank.get_events(event_id=events.event_id.values)
    
    analysis = parse_catalog(cat,stations_metadata,debug=False)
    analysis['contributor'] = contributor


    contributor_stations = analysis['stations_data']['good']

    # Save for global
    all_events.append(events[['longitude', 'latitude', 'magnitude']])
    all_stations.append(contributor_stations[['longitude', 'latitude']])

    region = compute_region(
        events, contributor_stations, padding=0.5, global_region=global_region)
    print("region",region)

    # === Plot ===
    fig = plt.figure(figsize=(12, 6), dpi=300)

    # Map
    ax_map = plt.subplot2grid((2, 3), (0, 0), rowspan=2, colspan=2, projection=ccrs.PlateCarree())
    eq = plot_network_map(events, contributor_stations, analysis, 
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
