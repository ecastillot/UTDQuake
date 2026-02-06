import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import ScalarFormatter
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import obsplus
from matplotlib.lines import Line2D
import obspy
from scipy.stats import linregress


from obspy.geodetics import locations2degrees, gps2dist_azimuth
from ..bank.utils import (merge_arrivals_and_picks, get_preferred_origins,
                                get_nth_arrival_time)

def compute_region(
    df_events,
    df_stations,
    padding=0.2,
    global_region=None,
    how="events",
    rm_outliers=False,
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

def human_format(num,pos=None):
    """
    Format large numbers with K/M suffix.

    Examples:
    999 -> '999'
    1200 -> '1.2K'
    1500000 -> '1.5M'
    """
    if abs(num) >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif abs(num) >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{num}"

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
    for l in [20, 50, 100, 200, 500, 1000, 5000, 10000, 20000, 50000, 100000]:
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

    # Calculate the scale bar extent
    x1 = x0
    x2 = x0 + scale_length_deg

    # Vertical position
    y1 = y0 - 0.1 * (lat_range * 0.02)  # Small pad under the line
    y2 = y0 + 0.1 * (lat_range * 0.02)  # Small pad above the line


    # Add white rectangle behind
    rect = mpatches.Rectangle(
        (x1, y1),  # lower left corner
        x2 - x1,   # width
        y2 - y1,   # height
        transform=ax.projection,
        facecolor='white',
        edgecolor='none',
        zorder=1   # draw below the line
    )
    ax.add_patch(rect)

    # Draw scale bar
    ax.plot(
        [x0, x0 + scale_length_deg],
        [y0, y0],
        transform=ax.projection,
        color='k',
        linewidth=4
    )

    ax.text(
        x0 + scale_length_deg / 2,
        y0 + y_pad * 0.7,
        f"{scale_length_km} km",
        ha='center',
        va='bottom',
        transform=ax.projection,
        fontsize=10,
        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.8)
    )

def smart_date_formatter(bins):
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
    import pandas as pd

    bins = pd.to_datetime(bins)
    years = bins.year.unique()
    months = bins.month.unique()

    if len(years) == 1 and len(months) == 1:
        # Case 1: Single month
        def fmt(x, pos=None):
            d = mdates.num2date(x)
            if pos == 0:
                return d.strftime("%Y\n%b")  # Year-Month on first tick
            return d.strftime("%d") if d.day <= 7 else ""  # Show day only at start of weeks
        return FuncFormatter(fmt)

    elif len(years) == 1 and len(months) > 1:
        # Case 2: Single year, multiple months
        def fmt(x, pos=None):
            d = mdates.num2date(x)
            if pos == 0:
                return d.strftime("%Y")  # First tick: Year
            if d.day <= 7:  # Show month at the first tick of each month
                return d.strftime("%b")
            return ""  # Otherwise empty
        return FuncFormatter(fmt)

    else:
        # Case 3: Multiple years
        def fmt(x, pos=None):
            d = mdates.num2date(x)
            if d.month == 1 and d.day <= 7:  # First tick in January: Year
                return d.strftime("%Y")
            if d.day <= 7:  # First tick of month
                return d.strftime("%b")
            return ""  # Otherwise empty
        return FuncFormatter(fmt)

def plot_overview(events, stations, analysis, 
                           region=None,
                output_file=None, show=True):
    """
    Plot a network map with events, stations, histograms, globe, and region.

    Parameters
    ----------
    events : pandas.DataFrame
        DataFrame with earthquake events.
    stations : pandas.DataFrame
        DataFrame with station data.
    analysis : dict
        Dictionary with info to show: must contain keys like
        'Contributor', 'events_total', 'stations_good', 'stations_bad',
        'p_arrivals_total', 's_arrivals_total'.
    region : tuple
        (lon_min, lon_max, lat_min, lat_max) for map extent.
    output_file : str, optional
        Path to save figure. If None, shows interactively.
    show : bool, optional
        Whether to show the plot interactively. Default is True.
    """
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cartopy
    import datetime
    from cartopy.mpl.geoaxes import GeoAxes
    from cartopy.geodesic import Geodesic
    
    # print(events.describe())
    if region is None:
        calculated_stations = stations[stations["calculated"]==True]
        gd_stations = calculated_stations.rename(columns={"calculated_longitude": "longitude",
                                                "calculated_latitude": "latitude",
                                                "calculated_elevation": "elevation"})
        region = compute_region(
                    events, gd_stations, padding=0.2, 
                    rm_outliers=True)

    fig = plt.figure(figsize=(12, 6))

    # Define the main grid: 2 columns
    gs = gridspec.GridSpec(2, 2, figure=fig, 
                            width_ratios=[2, 1], 
                            height_ratios=[0.7, 2], 
                            wspace=0.02, hspace=0.05)

    # Left column (col 0): split into two rows
    ax1 = fig.add_subplot(gs[0, 0])   # small top-left
    # ax2 = fig.add_subplot(gs[1, 0])  # big bottom-left

    # Right column (col 1): further subdivide into 3 rows
    gs_right = gridspec.GridSpecFromSubplotSpec(3, 1, 
                                                subplot_spec=gs[:, 1],
                                                hspace=0.6)

    ax3 = fig.add_subplot(gs_right[0, 0])   # top histogram
    ax4 = fig.add_subplot(gs_right[1, 0])   # middle histogram
    ax5 = fig.add_subplot(gs_right[2, 0])  # bottom histogram


    ax1.set_title(f"Contributor: {analysis.get('Contributor', 'N/A')}",
                  fontsize=14, weight='bold',loc='left')
    ax1.text(
        0.70, 0.8,
        f"Events: {human_format(analysis.get('Events', len(events)))}\n"
        f"Total Stations: {human_format(analysis['Total Stations'])}\n"
        f"   Calculated: {human_format(analysis['Calculated Stations'])}\n"
        f"   Confirmed: {human_format(analysis['Confirmed Stations'])}\n"
        f"P Arrivals: {human_format(analysis.get('P arrivals', 0))}\n"
        f"S Arrivals: {human_format(analysis.get('S arrivals', 0))}",
        transform=ax1.transAxes,
        ha='left',
        va='top',
        fontsize=9,
        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
    )
    ax1.set_axis_off()


    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Earthquakes',
               markerfacecolor="#ec7524", markersize=8, markeredgecolor='orange'),
        Line2D([0], [0], marker='^', color='w', label='Stations',
               markerfacecolor='green', markersize=8, markeredgecolor='green')
    ]
    ax1.legend(handles=legend_elements,
               loc='upper left',
            #    fontsize='x-small',
               bbox_to_anchor=(0.05, 0.7),
               frameon=True,
               fancybox=True,
               fontsize=10,
               framealpha=1,
               edgecolor='gray')
    
    ax1.set_axis_off()

    # Globe map
    eq_lon_mean = events['longitude'].mean()
    eq_lat_mean = events['latitude'].mean()
    
    ax1 = fig.add_subplot(gs[0, 0],
            projection=ccrs.Orthographic(
            central_longitude=eq_lon_mean,
            central_latitude=eq_lat_mean
        ))
    
    ax1.add_feature(cfeature.COASTLINE)
    ax1.add_feature(cfeature.OCEAN)
    ax1.add_feature(cfeature.LAND)
    ax1.add_feature(cfeature.STATES, linestyle=':')
    ax1.add_feature(cfeature.BORDERS, linestyle=':')
    # ax1.coastlines()

    ax1.set_global()
    ax1.scatter(
        stations['longitude'],
        stations['latitude'],
        marker='^',
        c='green',
        alpha=0.7,
        edgecolor='green',
        transform=ccrs.PlateCarree()
    )
    ax1.scatter(
        events['longitude'],
        events['latitude'],
        color="#ec7524",
        alpha=1,
        edgecolor="#ec7524",
        transform=ccrs.PlateCarree()
    )

    ax1.set_axis_off()


    # print(events.info())
    starttime = pd.to_datetime(events['time'].min())
    endtime = pd.to_datetime(events['time'].max())


    starttime = starttime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # endtime = endtime.replace(day=30, hour=0, minute=0, second=0, microsecond=0)
    print(f"Start time: {starttime}, End time: {endtime}")
    total_days = (endtime - starttime).days
    if total_days <= 30*3:
    # less than ~1 month → daily bins
        freq = 'D'
    elif total_days <= 365:
        # up to ~3 months → weekly bins
        freq = 'W'
    else:
        # longer → quarterly bins
        freq = '3MS'

    bins = pd.date_range(start=starttime, 
                         end=endtime, 
                         freq=freq).to_list()
    if bins[-1] < endtime:
        bins.append(endtime)
    # print(bins)
    # Right axis for counts (behind)
    ax3r = ax3.twinx()
    ax3r.hist(events["time"], bins=bins, 
            color='k', edgecolor='w', alpha=0.4, zorder=1)  # low alpha
    ax3r.set_ylabel('Counts')
    ax3r.yaxis.tick_right()
    ax3r.yaxis.set_label_position("right")
    ax3r.spines["right"].set_edgecolor('k')
    ax3r.spines["right"].set_linewidth(1)
    ax3r.tick_params(axis='y', colors='k')
    ax3r.spines['left'].set_visible(False)
    ax3r.grid(True, which='major', linestyle='--', alpha=0.5, zorder=0)

    formatter = mticker.ScalarFormatter()
    formatter.set_scientific(True)
    formatter.set_powerlimits((0, 0)) 
    ax3r.yaxis.set_major_formatter(formatter)

    formatter = smart_date_formatter(bins)
    ax3.xaxis.set_major_formatter(formatter)
    ax3.tick_params(axis="x", rotation=90)

    # Bold years on x-axis
    bold = False
    for label in ax3.get_xticklabels():
        txt = label.get_text()
        if len(txt) != 4:
            bold = True
            continue

    if bold:
        for label in ax3.get_xticklabels():
            txt = label.get_text()
            if txt.isdigit() and len(txt) == 4:   # crude check: YYYY
                label.set_fontweight("bold")


    # Left axis for magnitude (on top)
    ax3.scatter(events["time"], events["magnitude"], 
                s=1.5*(2**np.array(events["magnitude"])), 
                c='darkorange', edgecolor=None, alpha=0.5, zorder=5)  # higher zorder
    ax3.set_ylabel('Magnitude', color='darkorange')
    # ax3.set_xlabel('Time')
    ax3.set_ylim(-1, 7)
    ax3.yaxis.set_major_locator(MultipleLocator(2))  # ticks every 2
    ax3.yaxis.tick_left()
    ax3.yaxis.set_label_position("left")
    ax3.spines["left"].set_edgecolor('darkorange')
    ax3.spines["left"].set_linewidth(3)
    ax3.tick_params(axis='y', colors='darkorange')
    ax3.grid(True, linestyle='--', alpha=0.5,axis="x")


    if 'depth' in events.columns:
        depth_km = events['depth'].dropna() / 1e3

        # Compute limits
        lower, upper = np.percentile(depth_km, [1, 97])
        # Keep only the "central" data
        depth_filtered = depth_km[(depth_km >= lower) &\
                                   (depth_km <= upper)]


        # Depth histogram
        ax4.hist(depth_filtered, bins=20, color='green', alpha=0.7)
        ax4.yaxis.set_major_formatter(FuncFormatter(human_format))
        ax4.set_xlabel('Depth')
        ax4.set_ylabel('Counts')
        ax4.yaxis.tick_right()
        ax4.yaxis.set_label_position("right")
        ax4.grid(True, linestyle='--', alpha=0.5)

        formatter = mticker.ScalarFormatter()
        formatter.set_scientific(True)
        formatter.set_powerlimits((0, 0)) 
        ax4.yaxis.set_major_formatter(formatter)
    else:
        ax4.text(
            0.1, 0.5,
            f"No Depth Data",
            transform=ax4.transAxes,
            ha='left',
            va='bottom',
            fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
        )
        ax4.set_axis_off()

    m = events['magnitude'].dropna()
    if 'magnitude' in events.columns and len(m)!=0:
        # Magnitude histogram
        ax5.hist(m , bins=20, color='darkorange', alpha=0.7)
        ax5.yaxis.set_major_formatter(FuncFormatter(human_format))
        ax5.set_xlabel('Magnitude')
        ax5.set_ylabel('Counts')
        ax5.set_xlim(-1, 7)
        ax5.yaxis.tick_right()
        ax5.yaxis.set_label_position("right")
        ax5.grid(True, linestyle='--', alpha=0.5)

        formatter = mticker.ScalarFormatter()
        formatter.set_scientific(True)
        formatter.set_powerlimits((0, 0)) 
        ax5.yaxis.set_major_formatter(formatter)
    else:
        ax5.text(
            0.1, 0.5,
            f"No Magnitude Data",
            transform=ax5.transAxes,
            ha='left',
            va='bottom',
            fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
        )
        ax5.set_axis_off()

    

    # Region map
    ax2 = fig.add_subplot(gs[1, 0],
                        projection=ccrs.PlateCarree()
                    )
    
    ax2.set_extent(region, crs=ccrs.PlateCarree())
    ax2.add_feature(cfeature.COASTLINE)
    ax2.add_feature(cfeature.BORDERS, linestyle=':')
    ax2.add_feature(cfeature.STATES, linestyle=':')
    ax2.add_feature(cfeature.LAND)
    ax2.add_feature(cfeature.OCEAN)
    ax2.add_feature(cfeature.LAKES, alpha=0.5)

    ax2.scatter(
        events['longitude'],
        events['latitude'],
        color="#ec7524",
        alpha=1,
        edgecolor="#ec7524",
        transform=ccrs.PlateCarree()
    )
    ax2.scatter(
        stations['longitude'],
        stations['latitude'],
        marker='^',
        c='green',
        alpha=1,
        edgecolor='green',
        transform=ccrs.PlateCarree()
    )

    gl = ax2.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                       alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False

    # ax2.set_title(f"Contributor: {analysis.get('Contributor', 'N/A')}",
    #               fontsize=14, weight='bold',loc='left')

    add_scalebar(ax2, region, location='lower left')


    # plt.subplots_adjust(wspace=0.2, hspace=0.5)
    # plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300)
        print(f"Saved plot to {output_file}")
    if show:
        plt.show()

    plt.close(fig)

def plot_network_map(events, stations, region, analysis, 
                output_file=None, show=True):
    """
    Plot a network map with events, stations, histograms, globe, and region.

    Parameters
    ----------
    events : pandas.DataFrame
        DataFrame with earthquake events.
    stations : pandas.DataFrame
        DataFrame with station data.
    region : tuple
        (lon_min, lon_max, lat_min, lat_max) for map extent.
    analysis : dict
        Dictionary with info to show: must contain keys like
        'Contributor', 'events_total', 'stations_good', 'stations_bad',
        'p_arrivals_total', 's_arrivals_total'.
    output_file : str, optional
        Path to save figure. If None, shows interactively.
    show : bool, optional
        Whether to show the plot interactively. Default is True.
    """
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cartopy
    from cartopy.mpl.geoaxes import GeoAxes
    from cartopy.geodesic import Geodesic
    
    fig = plt.figure(figsize=(12, 6))
    gs = gridspec.GridSpec(3, 5, figure=fig,wspace=0.1, hspace=0.5)

    # Top-left text box
    ax1 = fig.add_subplot(gs[0, 0])

    # gd_stations = analysis['stations_good']
    # bad_stations = analysis['stations_bad']
    # total_stations = gd_stations + bad_stations

    ax1.text(
        0.10, 0.4,
        f"Events: {human_format(analysis.get('Events', len(events)))}\n"
        f"Total Stations: {human_format(analysis['Total Stations'])}\n"
        f"   Calculated: {human_format(analysis['Calculated Stations'])}\n"
        f"   Confirmed: {human_format(analysis['Confirmed Stations'])}\n"
        f"P Arrivals: {human_format(analysis.get('P arrivals', 0))}\n"
        f"S Arrivals: {human_format(analysis.get('S arrivals', 0))}",
        transform=ax1.transAxes,
        ha='left',
        va='top',
        fontsize=9,
        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
    )
    ax1.set_axis_off()

    ax3 = fig.add_subplot(gs[1, 0:2])
    if 'depth' in events.columns:
        # Depth histogram
        ax3.hist(events['depth'].dropna()/1e3, bins=20, color='blue', alpha=0.7)
        ax3.yaxis.set_major_formatter(FuncFormatter(human_format))
        ax3.set_xlabel('Depth')
        ax3.set_ylabel('Count')
        ax3.grid(True, linestyle='--', alpha=0.5)
    else:
        ax3.text(
            0.1, 0.5,
            f"No Depth Data",
            transform=ax3.transAxes,
            ha='left',
            va='bottom',
            fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
        )
        ax3.set_axis_off()

    ax4 = fig.add_subplot(gs[2:, 0:2])
    m = events['magnitude'].dropna()
    if 'magnitude' in events.columns and len(m)!=0:
        # Magnitude histogram
        ax4.hist(m , bins=20, color='green', alpha=0.7)
        ax4.yaxis.set_major_formatter(FuncFormatter(human_format))
        ax4.set_xlabel('Magnitude')
        ax4.set_ylabel('Count')
        ax4.grid(True, linestyle='--', alpha=0.5)
    else:
        ax4.text(
            0.1, 0.5,
            f"No Magnitude Data",
            transform=ax4.transAxes,
            ha='left',
            va='bottom',
            fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
        )
        ax4.set_axis_off()

    # Globe map
    eq_lon_mean = events['longitude'].mean()
    eq_lat_mean = events['latitude'].mean()
    ax2 = fig.add_subplot(
        gs[0, 1],
        projection=ccrs.Orthographic(
            central_longitude=eq_lon_mean,
            central_latitude=eq_lat_mean
        )
    )
    ax2.add_feature(cfeature.COASTLINE)
    ax2.add_feature(cfeature.OCEAN)
    ax2.add_feature(cfeature.LAND)
    ax2.add_feature(cfeature.STATES, linestyle=':')
    ax2.add_feature(cfeature.BORDERS, linestyle=':')
    # ax2.coastlines()

    ax2.set_global()
    ax2.scatter(
        stations['longitude'],
        stations['latitude'],
        marker='^',
        c='green',
        alpha=0.7,
        edgecolor='green',
        transform=ccrs.PlateCarree()
    )
    ax2.scatter(
        events['longitude'],
        events['latitude'],
        color="#ec7524",
        alpha=1,
        edgecolor="#ec7524",
        transform=ccrs.PlateCarree()
    )

    # Region map
    ax5 = fig.add_subplot(
        gs[:, 2:5],
        projection=ccrs.PlateCarree()
    )
    ax5.set_extent(region, crs=ccrs.PlateCarree())
    ax5.add_feature(cfeature.COASTLINE)
    ax5.add_feature(cfeature.BORDERS, linestyle=':')
    ax5.add_feature(cfeature.STATES, linestyle=':')
    ax5.add_feature(cfeature.LAND)
    ax5.add_feature(cfeature.OCEAN)
    ax5.add_feature(cfeature.LAKES, alpha=0.5)

    ax5.scatter(
        events['longitude'],
        events['latitude'],
        color="#ec7524",
        alpha=1,
        edgecolor="#ec7524",
        transform=ccrs.PlateCarree()
    )
    ax5.scatter(
        stations['longitude'],
        stations['latitude'],
        marker='^',
        c='green',
        alpha=1,
        edgecolor='green',
        transform=ccrs.PlateCarree()
    )

    gl = ax5.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                       alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.left_labels = False

    ax5.set_title(f"Contributor: {analysis.get('Contributor', 'N/A')}",
                  fontsize=14, weight='bold')

    add_scalebar(ax5, region, location='lower left')

    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Earthquakes',
               markerfacecolor='red', markersize=8, markeredgecolor='red'),
        Line2D([0], [0], marker='^', color='w', label='Stations',
               markerfacecolor='green', markersize=8, markeredgecolor='green')
    ]
    ax1.legend(handles=legend_elements,
               loc='upper left',
            #    fontsize='x-small',
               bbox_to_anchor=(0.05, 0.97),
               frameon=True,
               fancybox=True,
               fontsize=10,
               framealpha=1,
               edgecolor='gray')

    # plt.subplots_adjust(wspace=0.2, hspace=0.5)
    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300)
        print(f"Saved plot to {output_file}")
    if show:
        plt.show()

    plt.close(fig)

def plot_network_map2(events, stations, region, analysis, 
                output_file=None, show=True):
    """
    Plot a network map with events, stations, histograms, globe, and region.

    Parameters
    ----------
    events : pandas.DataFrame
        DataFrame with earthquake events.
    stations : pandas.DataFrame
        DataFrame with station data.
    region : tuple
        (lon_min, lon_max, lat_min, lat_max) for map extent.
    analysis : dict
        Dictionary with info to show: must contain keys like
        'Contributor', 'events_total', 'stations_good', 'stations_bad',
        'p_arrivals_total', 's_arrivals_total'.
    output_file : str, optional
        Path to save figure. If None, shows interactively.
    show : bool, optional
        Whether to show the plot interactively. Default is True.
    """
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cartopy
    from cartopy.mpl.geoaxes import GeoAxes
    from cartopy.geodesic import Geodesic
    
    fig = plt.figure(figsize=(12, 6))
    gs = gridspec.GridSpec(3, 5, figure=fig,wspace=0.1, hspace=0.5)

    # Top-left text box
    ax1 = fig.add_subplot(gs[0, 0])

    gd_stations = analysis['stations_good']
    bad_stations = analysis['stations_bad']
    total_stations = gd_stations + bad_stations

    ax1.text(
        0.11, 0.4,
        f"Events: {human_format(analysis.get('events_total', len(events)))}\n"
        f"Total Stations: {human_format(total_stations)}\n"
        f"Confirmed Stations: {human_format(gd_stations)}\n"
        f"P Arrivals: {human_format(analysis.get('p_arrivals_total', 0))}\n"
        f"S Arrivals: {human_format(analysis.get('s_arrivals_total', 0))}",
        transform=ax1.transAxes,
        ha='left',
        va='top',
        fontsize=10,
        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
    )
    ax1.set_axis_off()

    ax3 = fig.add_subplot(gs[1, 0:2])
    if 'depth' in events.columns:
        # Depth histogram
        ax3.hist(events['depth'].dropna()/1e3, bins=20, color='blue', alpha=0.7)
        ax3.yaxis.set_major_formatter(FuncFormatter(human_format))
        ax3.set_xlabel('Depth')
        ax3.set_ylabel('Count')
        ax3.grid(True, linestyle='--', alpha=0.5)
    else:
        ax3.text(
            0.1, 0.5,
            f"No Depth Data",
            transform=ax3.transAxes,
            ha='left',
            va='bottom',
            fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
        )
        ax3.set_axis_off()

    ax4 = fig.add_subplot(gs[2:, 0:2])
    m = events['magnitude'].dropna()
    if 'magnitude' in events.columns and len(m)!=0:
        # Magnitude histogram
        ax4.hist(m , bins=20, color='green', alpha=0.7)
        ax4.yaxis.set_major_formatter(FuncFormatter(human_format))
        ax4.set_xlabel('Magnitude')
        ax4.set_ylabel('Count')
        ax4.grid(True, linestyle='--', alpha=0.5)
    else:
        ax4.text(
            0.1, 0.5,
            f"No Magnitude Data",
            transform=ax4.transAxes,
            ha='left',
            va='bottom',
            fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
        )
        ax4.set_axis_off()

    # Globe map
    eq_lon_mean = events['longitude'].mean()
    eq_lat_mean = events['latitude'].mean()
    ax2 = fig.add_subplot(
        gs[0, 1],
        projection=ccrs.Orthographic(
            central_longitude=eq_lon_mean,
            central_latitude=eq_lat_mean
        )
    )
    ax2.add_feature(cfeature.COASTLINE)
    ax2.add_feature(cfeature.OCEAN)
    ax2.add_feature(cfeature.LAND)
    ax2.add_feature(cfeature.STATES, linestyle=':')
    ax2.add_feature(cfeature.BORDERS, linestyle=':')
    # ax2.coastlines()

    ax2.set_global()
    ax2.scatter(
        stations['longitude'],
        stations['latitude'],
        marker='^',
        c='green',
        alpha=0.7,
        edgecolor='green',
        transform=ccrs.PlateCarree()
    )
    ax2.scatter(
        events['longitude'],
        events['latitude'],
        color='red',
        alpha=1,
        edgecolor='red',
        transform=ccrs.PlateCarree()
    )

    # Region map
    ax5 = fig.add_subplot(
        gs[:, 2:5],
        projection=ccrs.PlateCarree()
    )
    ax5.set_extent(region, crs=ccrs.PlateCarree())
    ax5.add_feature(cfeature.COASTLINE)
    ax5.add_feature(cfeature.BORDERS, linestyle=':')
    ax5.add_feature(cfeature.STATES, linestyle=':')
    ax5.add_feature(cfeature.LAND)
    ax5.add_feature(cfeature.OCEAN)
    ax5.add_feature(cfeature.LAKES, alpha=0.5)

    ax5.scatter(
        events['longitude'],
        events['latitude'],
        color='red',
        alpha=1,
        edgecolor='red',
        transform=ccrs.PlateCarree()
    )
    ax5.scatter(
        stations['longitude'],
        stations['latitude'],
        marker='^',
        c='green',
        alpha=1,
        edgecolor='green',
        transform=ccrs.PlateCarree()
    )

    gl = ax5.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                       alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.left_labels = False

    ax5.set_title(f"Contributor: {analysis.get('Contributor', 'N/A')}",
                  fontsize=14, weight='bold')

    add_scalebar(ax5, region, location='lower left')

    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Earthquakes',
               markerfacecolor='red', markersize=8, markeredgecolor='red'),
        Line2D([0], [0], marker='^', color='w', label='Stations',
               markerfacecolor='green', markersize=8, markeredgecolor='green')
    ]
    ax1.legend(handles=legend_elements,
               loc='upper left',
            #    fontsize='x-small',
               bbox_to_anchor=(0.05, 0.97),
               frameon=True,
               fancybox=True,
               fontsize=10,
               framealpha=1,
               edgecolor='gray')

    # plt.subplots_adjust(wspace=0.2, hspace=0.5)
    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300)
        print(f"Saved plot to {output_file}")
    if show:
        plt.show()

    plt.close(fig)

def create_green_to_orange_cmap(name='green_to_orange', n_colors=256):
    """
    Create a colormap that goes from green to a specific orange (#ec7524).

    Parameters:
    - name: str, name of the colormap
    - n_colors: int, number of discrete colors in the colormap

    Returns:
    - cmap: matplotlib.colors.LinearSegmentedColormap object
    """
    colors = ['green', '#ec7524']
    cmap = LinearSegmentedColormap.from_list(name, colors, N=n_colors)
    return cmap

def plot_stats(events, picks=None, savepath=None):
    """
    Create a 5-panel seismic overview figure:
    - Depth histogram
    - Magnitude histogram
    - Epicentral distance distribution (requires picks)
    - Azimuthal gap (from events)
    - Azimuth distribution (requires picks)
    
    Parameters
    ----------
    events : pandas.DataFrame
        DataFrame with columns: ['time', 'depth', 'magnitude', 'azimuthal_gap', ...]
    picks : pandas.DataFrame or None, optional
        If provided, used to plot epicentral distance and azimuth.
    savepath : str or None, optional
        If provided, saves the figure to this path with dpi=300.
        If None, just returns fig and axes without saving.
    
    Returns
    -------
    fig : matplotlib.figure.Figure
    axes : dict of matplotlib.axes.Axes
    """

    fig = plt.figure(figsize=(10, 8)) 
    gs = gridspec.GridSpec(2, 4, figure=fig)
    ax1 = fig.add_subplot(gs[0, 0:2]) # Depth 
    ax2 = fig.add_subplot(gs[0, 2:4]) # Magnitude 
    ax3 = fig.add_subplot(gs[1, 1:3]) # Epicentral distance (needs picks) 
    ax4 = fig.add_subplot(gs[1, 0], projection="polar") # Azimuthal gap (events) 
    ax5 = fig.add_subplot(gs[1, 3], projection="polar") # Azimuth (needs picks)

    axes = [ax1, ax2, ax4, ax3, ax5]
    labels = ['(a)', '(b)', '(c)', '(d)', '(e)']
    for ax, label in zip(axes, labels):
        ax.text(-0.1, 1.05, label, transform=ax.transAxes,
                fontsize=12, fontweight='bold', va='bottom', ha='right')

    # --- Depth histogram ---
    depth_km = events['depth'].dropna() / 1e3
    lower, upper = np.percentile(depth_km, [1, 97])
    depth_filtered = depth_km[(depth_km >= lower) & (depth_km <= upper)]
    ax1.hist(depth_filtered, bins=20, color='#006400', alpha=0.7)
    ax1.set_yscale("log")
    ax1.set_xlabel('Depth [km]')
    ax1.set_ylabel('Log Frequency')
    ax1.set_title("Depth")
    ax1.set_ylim(bottom=1)
    ax1.grid(True, linestyle='--', alpha=0.5)

    # --- Magnitude histogram ---
    ax2.hist(events['magnitude'], bins=20, color='#ec7524')
    ax2.set_yscale("log")
    ax2.set_title("Magnitude")
    ax2.set_xlabel("Magnitude")
    ax2.set_ylabel("Log Frequency")
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.set_ylim(bottom=1)
    max_mag, min_mag = events['magnitude'].max(), events['magnitude'].min()
    ax2.annotate(f"Max: {max_mag:.2f}", xy=(0.98, 0.95),
                 xycoords="axes fraction", ha="right", fontsize=9)
    ax2.annotate(f"Min: {min_mag:.2f}", xy=(0.98, 0.88),
                 xycoords="axes fraction", ha="right", fontsize=9)

    # --- Epicentral distance (picks-dependent) ---
    if picks is None:
        ax3.text(0.5, 0.5, "No picks available", ha='center', va='center')
        ax3.set_title("Epicentral Distance")
    else:
        # Prepare bins and labels
        bins = [0, 30, 60, 100, 150, 200, 300, np.inf]
        labels_dist = [
            f">{int(bins[i])}" if bins[i+1] == np.inf else f"{int(bins[i])}-{int(bins[i+1])}"
            for i in range(len(bins)-1)
        ]

        picks["distance_km"] = picks['distance'] * 111

        # Split by phase
        picks_P = picks[picks["phase"] == "P"]
        picks_S = picks[picks["phase"] == "S"]

        # Histogram counts
        counts_P, _ = np.histogram(picks_P["distance_km"], bins=bins)
        counts_S, _ = np.histogram(picks_S["distance_km"], bins=bins)

        # Percentages
        pct_P = 100 * counts_P / counts_P.sum()
        pct_S = 100 * counts_S / counts_S.sum()

        # Plot
        y_pos = np.arange(len(labels_dist))

        # Mirrored bars
        ax3.barh(
            y_pos,
            -counts_P,        # negative (left side)
            color="#006400",
            alpha=0.7,
            edgecolor="k",
            label="P"
        )

        ax3.barh(
            y_pos,
            counts_S,         # positive (right side)
            color='#ec7524',
            alpha=0.7,
            edgecolor="k",
            label="S"
        )

        ax3.axvline(0, color='k', linewidth=1)  # center line

        # Labels
        # Show y-ticks and labels only on the right
        ax3.yaxis.set_ticks_position('both')            # ticks on the right
        ax3.tick_params(axis='y', labelleft=True, labelright=False, pad=5)
        ax3.set_yticks(y_pos)
        ax3.set_yticklabels(labels_dist)
        # ax3.set_yticks(y_pos)
        # ax3.set_yticklabels(labels_dist)
        
        ax3.invert_yaxis()
        ax3.set_xlabel("Counts")
        ax3.set_ylabel("Distance (km)", rotation=90, 
                       va='bottom', ha='center')
        ax3.set_title("Epicentral Distance by Phase")

        # Add percentages at the end of each bar
        for i in range(len(y_pos)):
            if counts_P[i] > 0:
                ax3.text(
                    -counts_P[i] - 1.5,
                    i,
                    f"{pct_P[i]:.1f}%",
                    va="center",
                    ha="right",
                    fontsize=9,
                    color="black",
                    rotation=90
                )
            if counts_S[i] > 0:
                ax3.text(
                    counts_S[i] + 1.5,
                    i,
                    f"{pct_S[i]:.1f}%",
                    va="center",
                    ha="left",
                    fontsize=9,
                    color="black",
                    rotation=-90
                )

        # Adjust x-limits to avoid clipping big bars
        max_val = max(counts_S.max(), counts_P.max())
        ax3.set_xlim(-(max_val * 1.15), max_val * 1.15)

        # Show y-ticks on both sides
        
        # ax3.yaxis.set_ticks_position('right')      # ticks on left and right
        # ax3.yaxis.set_tick_params(labelright=True, labelleft=True)  # labels on both
    
        ax3.grid(True, axis="both", linestyle="--", color="gray", alpha=0.5)
        ax3.ticklabel_format(style="sci", axis="x", scilimits=(0,0))
        ax3.legend(loc="lower right")


    # --- Azimuthal gap (from events) ---
    bins = 12
    azimuth_rad = np.deg2rad(events["azimuthal_gap"].values)
    counts, bin_edges = np.histogram(azimuth_rad, bins=bins, range=(0, 2*np.pi))
    angles = (bin_edges[:-1] + bin_edges[1:]) / 2
    percentages = 100 * counts / counts.sum()
    cmap = create_green_to_orange_cmap(n_colors=bins)
    norm = mcolors.Normalize(vmin=percentages.min(), vmax=percentages.max())
    colors = [(r, g, b, 0.7) for r, g, b, _ in cmap(norm(percentages))]
    ax4.bar(angles, np.ones_like(counts), width=2*np.pi/bins, bottom=0,
            align="center", edgecolor="k", color=colors)
    ax4.plot(0, 0, marker="*", color="black", markersize=18, zorder=5)
    ax4.set_theta_zero_location("N")
    ax4.set_theta_direction(-1)
    ax4.set_yticks([])
    ax4.set_thetagrids(np.arange(0, 360, 30))
    ax4.set_title("Azimuthal Gap", pad=25)

    # --- Add colorbar for azimuthal gap ---
    sm_gap = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm_gap.set_array([])
    cax_gap = inset_axes(ax4, width="80%", height="10%", loc="lower center", borderpad=-3)
    cbar_gap = plt.colorbar(sm_gap, cax=cax_gap, orientation="horizontal")
    cbar_gap.set_label("Percentage [%]")

    # --- Azimuth (picks-dependent) ---
    if picks is None:
        ax5.text(0.5, 0.5, "No picks available", ha='center', va='center', transform=ax5.transAxes)
        ax5.set_title("Azimuth")
    else:
        #no matter the phase
        # print(len(picks))
        picks = picks.drop_duplicates(subset=["origin_id", "network",
                                              "station"])
        # print(len(picks))
        bins = 12
        azimuth_rad = np.deg2rad(picks["azimuth"].values)
        counts, bin_edges = np.histogram(azimuth_rad, bins=bins, range=(0, 2*np.pi))
        angles = (bin_edges[:-1] + bin_edges[1:]) / 2
        percentages = 100 * counts / counts.sum()
        cmap = create_green_to_orange_cmap(n_colors=bins)
        colors = [(r, g, b, 0.7) for r, g, b, _ in cmap(norm(percentages))]
        ax5.bar(angles, np.ones_like(counts), width=2*np.pi/bins, bottom=0,
                align="center", edgecolor="k", color=colors)
        ax5.plot(0, 0, marker="^", color="black", markersize=14, zorder=5)
        ax5.set_theta_zero_location("N")
        ax5.set_theta_direction(-1)
        ax5.set_yticks([])
        ax5.set_thetagrids(np.arange(0, 360, 30))
        ax5.set_title("Azimuth", pad=25)

        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cax = inset_axes(ax5, width="80%", height="10%", loc="lower center", borderpad=-3) # tweak position/size
        cbar = plt.colorbar(sm, cax=cax, orientation="horizontal")
        cbar.set_label("Percentage [%]")

    plt.tight_layout()

    pos = ax5.get_position()  # get current position: Bbox(x0, y0, x1, y1)
    # adjust position: (x0, y0, width, height)
    ax5.set_position([pos.x0 - 0.05, pos.y0, 
                      pos.width, pos.height])  # move slightly right
    
    pos = ax3.get_position()  # get current position: Bbox(x0, y0, x1, y1)
    ax3.set_position([pos.x0 + 0.02, pos.y0, 
                      pos.width, pos.height])  # move slightly right
    
    if savepath:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")
        print(f"Saved plot to {savepath}")
    else:
        plt.show()

    axes_dict = {
        'depth': ax1,
        'magnitude': ax2,
        'epicentral_distance': ax3,
        'azimuthal_gap': ax4,
        'azimuth': ax5
    }
    return fig, axes_dict

def plot_uncertainty_boxplots(df, figsize=(4, 6), dpi=300, save_path=None):
    """
    Create a figure with two axes:
    1. Boxplots for Horizontal and Vertical uncertainty (km)
    2. Boxplot for Standard error

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns 'horizontal_uncertainty', 'vertical_uncertainty', 'standard_error'
    figsize : tuple
        Figure size
    dpi : int
        Resolution of the figure
    save_path : str or None
        If given, save the figure to this path instead of showing it.
    """
    fig, axes = plt.subplots(2, 1, figsize=figsize, dpi=dpi)

    # --- Prepare uncertainties in km ---
    df_hu = df["horizontal_uncertainty"].dropna() / 1e3
    df_vu = df["vertical_uncertainty"].dropna() / 1e3
    df_se = df["standard_error"].dropna()

    # --- Axis 1: Horizontal & Vertical uncertainties ---
    df_unc = pd.DataFrame({
        "Horizontal": df_hu,
        "Vertical": df_vu
    })
    sns.boxplot(data=df_unc, ax=axes[0], 
                # palette=["#ec7524", "green"],
                # saturation=0.5,
                boxprops=dict(facecolor='none', edgecolor='black'),  # 'none' makes it transparent
                medianprops=dict(color='black'),
                whiskerprops=dict(color='black'),
                capprops=dict(color='black'),
                showfliers=False),
    axes[0].set_ylabel("Uncertainty (km)")
    axes[0].set_title("Horizontal and Vertical Uncertainties")

    # --- Axis 2: Standard Error ---
    sns.boxplot(x=df_se, ax=axes[1], 
                boxprops=dict(facecolor='none', edgecolor='black'),  # 'none' makes it transparent
                medianprops=dict(color='black'),
                whiskerprops=dict(color='black'),
                capprops=dict(color='black'),
                showfliers=False)
    axes[1].set_xlabel("RMS")
    axes[1].set_title("Standard Error")

    axes = [axes[0],axes[1]]
    labels = ['(a)', '(b)']
    for ax, label in zip(axes, labels):
        ax.text(-0.1, 1.05, label, transform=ax.transAxes,
                fontsize=12, 
                fontweight='bold',
                  va='bottom', ha='right')


    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()

    return fig, axes


def plot_pick_histograms(df, save_path=None):
    """
    Plots three histograms:
    1. Number of P picks per origin
    2. Number of S picks per origin
    3. Vp/Vs ratio histogram using Wadati method
    
    Args:
        df (pd.DataFrame): DataFrame containing picks with columns:
            ['phase', 'origin_id', 'origin_time', 'time']
        save_path (str, optional): Path to save the figure. If None, shows the figure.
    Returns:
        fig, axes: Figure and axes objects
    """
    from scipy.stats import linregress

    # -------------------------------
    # 1. Count P and S picks per origin
    # -------------------------------
    p_counts = df[df['phase'].str.upper() == 'P'].groupby('origin_id').size()
    s_counts = df[df['phase'].str.upper() == 'S'].groupby('origin_id').size()

    # -------------------------------
    # 2. Calculate Vp/Vs ratios per origin using Wadati method
    # -------------------------------
    vp_vs_ratios = []
    ps_counts = []
    only_p_count = 0
    for origin_id, group in df.groupby('origin_id'):
        group = group.copy()
        # Calculate S-P times
        s_group = group[group['phase'].str.upper() == 'S']
        p_group = group[group['phase'].str.upper() == 'P']

        if len(s_group) == 0:
            only_p_count += 1
        elif len(p_group) == 0:
            continue  # Skip events with no P picks
        else:
            ps_counts.append(len(p_group)/len(s_group))


        # Merge S and P by seed_id to find S-P pairs
        merged = pd.merge(
            s_group[['network','station', 'time']], 
            p_group[['network','station', 'time']], 
            on=['network','station'], 
            suffixes=('_S', '_P')
        )

        merged = merged.drop_duplicates()
        if len(merged) < 2:
            continue  # Skip events with less than 2 S-P pairs

        merged['S_minus_P'] = merged['time_S'] - merged['time_P']

        merged["tt_SP"] = merged["S_minus_P"].dt.total_seconds()
        merged["tt_P"] = (merged["time_P"] - group['origin_time'].iloc[0]).dt.total_seconds()
        
        # Linear regression: S-P vs P times
        lr = linregress(merged['tt_P'], merged['tt_SP'])
        slope = lr.slope
        vp_vs_ratio = 1 + slope  # Wadati relation
        # print(f"Origin ID: {origin_id}, Vp/Vs Ratio: {vp_vs_ratio}")
        vp_vs_ratios.append(vp_vs_ratio)

    # -------------------------------
    # 3. Plot histograms
    # -------------------------------
    # fig, axes = plt.subplots(3, 1, figsize=(10, 12))


    fig = plt.figure(figsize=(8, 6))

    # Define the main grid: 2 columns
    gs = gridspec.GridSpec(2, 2, figure=fig, 
                           height_ratios=[2, 0.7],
                            # width_ratios=[2, 1], 
                            # height_ratios=[0.7, 2], 
                            # wspace=0.02, hspace=0.05
                            )

    # Left column (col 0): split into two rows
    ax1 = fig.add_subplot(gs[0, :])   # small top-left
    ax2 = fig.add_subplot(gs[1, 0])  # big bottom-left
    ax3 = fig.add_subplot(gs[1, 1])  # big bottom-left


    step=5
    picks_max = max(p_counts.max(), s_counts.max())
    closest = step * round(picks_max / step)
    # print(closest)

    # P picks
    bins = int(closest)
    counts_p, bin_edges_p, patches_p = ax1.hist(p_counts.values, range=(0,closest),
                 bins=bins, color='green', edgecolor='black',
                 linewidth=0.5, label = 'P',align="mid")
    counts_s, bin_edges_s, patches_s = ax1.hist(s_counts.values, range=(0,closest),
                 bins=bins, color='lightgreen', edgecolor='black',
                 weights=np.ones_like(s_counts.values)*-1,
                 linewidth=0.5, label = 'S',align="mid")
    ax1.set_title('Number of Picks per Event')
    ax1.set_xlabel('Number of Picks')
    ax1.set_ylabel('Frequency')

    yticks = ax1.get_yticks()
    ax1.set_yticklabels([abs(int(y)) for y in yticks])

    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend()
    
    # S picks
    ps_counts = np.array(ps_counts)
    # ax2.hist(ps_counts, bins=20, color='salmon', edgecolor='black')
    sns.boxplot(x=ps_counts, ax=ax2, 
                boxprops=dict(facecolor='none', edgecolor='black'),  # 'none' makes it transparent
                medianprops=dict(color='black'),
                whiskerprops=dict(color='black'),
                capprops=dict(color='black'),
                showfliers=False
                )
    # ax2.set_title('Proportion of P to S Picks per Event')
    ax2.set_xlabel('P Counts/S Counts Proportion')

    # Add annotation for events with only P picks
    total_events = len(df['origin_id'].unique())
    if only_p_count > 0:
        pct_only_p = only_p_count / total_events * 100
        ax2.text(0.05, 1.15, f"{pct_only_p:.1f}% only P phases",
                transform=ax2.transAxes,
                ha='left', va='top',
                fontsize=10, color='k')
    # ax2.set_ylabel('Frequency')
    
    # Vp/Vs ratio
    # ax3.hist(vp_vs_ratios, bins=20, color='lightgreen', edgecolor='black')
    sns.boxplot(x=vp_vs_ratios, ax=ax3, 
                boxprops=dict(facecolor='none', edgecolor='black'),  # 'none' makes it transparent
                medianprops=dict(color='black'),
                whiskerprops=dict(color='black'),
                capprops=dict(color='black'),
                showfliers=False
                )
    # ax3.set_title('Vp/Vs Ratio per Event')
    ax3.set_xlabel('Vp/Vs Ratio')
    # ax3.set_ylabel('Frequency')

    axes = [ax1,ax2,ax3]
    labels = ['(a)', '(b)','(c)']
    for ax, label in zip(axes, labels):
        ax.text(-0.1, 1.05, label, transform=ax.transAxes,
                fontsize=12, 
                fontweight='bold',
                  va='bottom', ha='right')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)
    else:
        plt.show()

    return fig

def plot_pick_stats(df, save_path=None):

    """
    Plot summary statistics for seismic picks (P, S, and S-P) as jointplots.

    This function computes:
    - First/last P travel times per event
    - First/last S travel times per event
    - First/last S-P times for stations that have both P and S picks
    - Corresponding epicentral distances (converted to km)

    It creates individual seaborn jointplots (scatter + marginal histograms),
    saves them temporarily as PNGs, and then combines them into a single
    multi-panel matplotlib figure.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing pick information. Expected columns include:
        - "origin_id"
        - "origin_time"
        - "time"
        - "phase"
        - "distance" (in degrees)
        - "network"
        - "station"
    save_path : str or pathlib.Path, optional
        If provided, the final combined figure is saved to this path.

    Returns
    -------
    matplotlib.figure.Figure
        The combined multi-panel figure containing all jointplots.
    """
    
    import seaborn as sns
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    import tempfile
    import os
    import string

    green = "#007A33"
    orange = "#ec7524"

    df["distance_km"] = df['distance'] * 111

    # Get first/last P/S arrivals
    first_p = df[df['phase'].str.upper() == 'P'].sort_values('time').groupby('origin_id').first()
    last_p  = df[df['phase'].str.upper() == 'P'].sort_values('time').groupby('origin_id').last()
    first_s = df[df['phase'].str.upper() == 'S'].sort_values('time').groupby('origin_id').first()
    last_s  = df[df['phase'].str.upper() == 'S'].sort_values('time').groupby('origin_id').last()

    first_p["tt_first_P"] = (first_p["time"] - first_p["origin_time"]).dt.total_seconds()
    last_p["tt_last_P"]   = (last_p["time"] - last_p["origin_time"]).dt.total_seconds()
    first_s["tt_first_S"] = (first_s["time"] - first_s["origin_time"]).dt.total_seconds()
    last_s["tt_last_S"]   = (last_s["time"] - last_s["origin_time"]).dt.total_seconds()

    # analyze stations by network and stations with P and S picks

    p_group = df[df['phase'].str.upper() == 'P']
    s_group = df[df['phase'].str.upper() == 'S']
    # Find stations with both P and S picks
    common_stations = pd.merge(
        s_group[['network','station',"origin_id","distance_km","time"]],
        p_group[['network','station',"origin_id","distance_km","time"]],  
        on=['network','station',"origin_id","distance_km"],
        suffixes=('_S', '_P')
    )
    common_stations = common_stations.drop_duplicates(subset=['network','station',"origin_id"])
    common_stations["tt_SP"] = (common_stations["time_S"] - common_stations["time_P"]).dt.total_seconds()

    first_sp = common_stations.sort_values('tt_SP').groupby('origin_id').first()
    last_sp  = common_stations.sort_values('tt_SP').groupby('origin_id').last()

    datasets = [
        (first_p, "tt_first_P", "distance_km", "First P Arrivals", "#ec7524", "#ec7524"),
        (last_p,  "tt_last_P",  "distance_km", "Last P Arrivals", "#ec7524", "#ec7524"),
        (first_s, "tt_first_S", "distance_km", "First S Arrivals", "green", "green"),
        (last_s,  "tt_last_S",  "distance_km", "Last S Arrivals", "green", "green"),
        (first_sp, "tt_SP", "distance_km", "First S-P Picks", "black", "black"),
        (last_sp,  "tt_SP", "distance_km", "Last S-P Picks", "black", "black"),
    ]

    labels = {"tt_first_P": "First P Arrival Time (s)",
              "tt_last_P": "Last P Arrival Time (s)",
              "tt_first_S": "First S Arrival Time (s)",
              "tt_last_S": "Last S Arrival Time (s)",
              "tt_SP": "S-P Time (s)",
              "distance_km": "Epicentral Distance (km)"}

    temp_files = []
    # hist_range = (0, 50)  # pick a global range covering all datasets
    ilabels = [f"({letter})" for letter in string.ascii_lowercase]

    # Step 1: create jointplots and save temporarily
    for i,(data, x, y, title, scatter_color, marginal_color) in enumerate(datasets):
        if data.empty:
            continue
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_files.append(tmp.name)

        g = sns.jointplot(
            data=data, x=x, y=y, kind="scatter", height=4,
            color=scatter_color,
            marginal_kws=dict(bins=20, fill=True, 
                              color=marginal_color),
            # xlim=hist_range,
            # ylim=hist_range
        )

        ilabel = f"({string.ascii_lowercase[i]})"
        g.fig.text(
                    0.05, 0.95,  # x,y in figure coordinates (0–1)
                    ilabel,
                    fontsize=12,
                    fontweight='bold',
                    va='top', ha='left'
                )

        g.ax_joint.grid(True, linestyle='--', alpha=0.5)  # grid for scatter
        g.set_axis_labels(labels[x], labels[y])
        g.fig.suptitle(title)
        g.fig.tight_layout()
        g.fig.subplots_adjust(top=0.9)
        g.fig.savefig(tmp.name, dpi=300)
        plt.close(g.fig)

    # Step 2: create master figure and reload images
    fig, axes = plt.subplots(3, 2, figsize=(6,10))
    axes = axes.flatten()

    for ax, img_file, label in zip(axes, temp_files,labels):
        img = mpimg.imread(img_file)
        ax.imshow(img)
        ax.axis('off')

    # labels = [f"({letter})" for letter in string.ascii_lowercase]
    # for ax, label in zip(axes, labels):
    #     ax.text(
    #         -0.1, 1.05, label, 
    #         transform=ax.transAxes,
    #         fontsize=12,
    #         fontweight='bold',
    #         va='bottom', ha='right'
    #     )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)

    # Clean up temporary files
    for f in temp_files:
        os.remove(f)

    # plt.show()
    return fig



def plot_station_location_uncertainty(df, save_path,  dpi=300):
    """
    Compare confirmed vs calculated latitude and longitude in a DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing confirmed_latitude, confirmed_longitude,
        calculated_latitude, and calculated_longitude columns.
    save_path : str
        File path to save the output plot (e.g., 'output.png').
    dpi : int, default=300
        Resolution of the saved figure.
    """
    import cartopy.crs as ccrs
    # Compute differences
    dlat = df["calculated_latitude"] - df["confirmed_latitude"]
    dlon = df["calculated_longitude"] - df["confirmed_longitude"]
    
    mean_lat = np.radians(df["confirmed_latitude"].mean())
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * np.cos(mean_lat)
    
    dlat_km = dlat * km_per_deg_lat
    dlon_km = dlon * km_per_deg_lon

    # # Convert to kilometers if requested
    # if to_km:
    #     # Approximate conversions (1° latitude ≈ 111 km)
    #     unit = "km"
    # else:
    #     unit = "°"

    # Number of stations
    n_stations = len(df)
    
    
    # Create figure
    fig,axes = plt.subplots(2,1,figsize=(6, 8), dpi=dpi)
    
    fig2, ax = plt.subplots(
                            1, 1,
                            subplot_kw={"projection": ccrs.PlateCarree()},
                            figsize=(8, 6)
                        )
    # AX1 spans two cells horizontally (big)
    # ax1 = fig.add_subplot(gs[0, 0:3],projection=ccrs.PlateCarree())   # Row 0, columns 0 & 1
    _df = df.rename(columns={"calculated_latitude": "latitude",
                            "calculated_longitude": "longitude"})
    region = compute_region(_df,df,padding=0.05)
    # print(region)
    plot_station_map(ax, df,region)
    

    
    ax3, ax4 = axes
    # Scatter plot
    ax3.scatter(dlon_km, dlat_km, s=3, alpha=0.4,color="green")
    ax3.axhline(0, color="gray", linestyle="--", lw=0.8)
    ax3.axvline(0, color="gray", linestyle="--", lw=0.8)
    ax3.set_xlabel(f"Δ Longitude (km)")
    ax3.set_ylabel(f"Δ Latitude (km)")
    ax3.set_title("Spatial Difference (Calculated - Confirmed)")
    ax3.grid(True, linestyle="--", alpha=0.3)
    ax3.text(0.95, 0.95, f"Stations: {n_stations}",
               transform=ax3.transAxes, ha='right', va='top',
               fontsize=10, fontweight='bold', color='black')
    
    # Compute distance difference
    distance = np.sqrt(dlat_km**2 + dlon_km**2)
    # Histogram of total difference
    ax4.hist(distance, bins=50, color="green", alpha=0.7)
    ax4.set_xlabel(f"Epicentral Difference (km)")
    ax4.set_ylabel("Count")
    ax4.set_title("Distribution of Spatial Differences")
    ax4.grid(True, linestyle="--", alpha=0.3)
    
    fig.tight_layout()
    if save_path is not None:
        fig.savefig(save_path, dpi=dpi)
        fig2.savefig(save_path.replace('.png','_map.png'), dpi=dpi)
    else:
        plt.show()

    plt.close(fig)
    
    print(f"Plot saved to {save_path}")
    # print(f"Mean total difference: {distance.mean():.4f} km")

def plot_venn(ax, df):
    """Draw Venn diagram of calculated vs confirmed stations."""
    from matplotlib_venn import venn2

    calc = df['calculated'].sum()
    conf = df['confirmed'].sum()
    inter = ((df['calculated'] == 1) & (df['confirmed'] == 1)).sum()

    only_calc = max(calc - inter, 0)
    only_conf = max(conf - inter, 0)
    inter = max(inter, 0)

    v = venn2(
        subsets=(only_calc, only_conf, inter),
        set_labels=('Calculated', 'Calculated &\nConfirmed'),
        set_colors=('green', 'white'),
        alpha=0.7,
        ax=ax
    )

    # Color intersection
    if v.get_patch_by_id('11'):
        v.get_patch_by_id('11').set_color('gray')

    # Reposition labels
    if v.get_label_by_id('10'):
        v.get_label_by_id('10').set_position((-0.4, 0))

    if v.get_label_by_id('11'):
        v.get_label_by_id('11').set_position((0.1, -0.1))

    # Style
    for lbl in v.set_labels:
        if lbl:
            lbl.set_fontsize(16)
            lbl.set_fontweight("bold")

    for sub in v.subset_labels:
        if sub:
            sub.set_fontsize(16)

    return ax

def setup_map(ax, region):
    """Configure a cartopy map axis."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    ax.set_extent(region, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.STATES, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='gray')
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)

    gl = ax.gridlines(draw_labels=True, linewidth=0.8, color='gray',
                      alpha=0.7, linestyle='--')
    gl.top_labels = True
    gl.left_labels = True
    gl.right_labels = False
    gl.bottom_labels = True
    return ax

def plot_station_map(ax, df,  region):
    """Plot calculated and confirmed station locations."""
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    ax = setup_map(ax, region)

    mask = (df['confirmed'] == 1) & (df['calculated'] == 1)
    df_diff = df.loc[mask, [
        'network', 'station',
        'confirmed_latitude', 'confirmed_longitude',
        'calculated_latitude', 'calculated_longitude'
    ]]

    # All calculated stations
    ax.scatter(
        df['calculated_longitude'],
        df['calculated_latitude'],
        marker='^', c='green', s=40, alpha=0.7,
        transform=ccrs.PlateCarree(),
        label='Calculated'
    )

    # Stations with both
    ax.scatter(
        df_diff['calculated_longitude'],
        df_diff['calculated_latitude'],
        marker='^', c='gray', s=40, alpha=0.7,
        transform=ccrs.PlateCarree(),
        label='Calculated & Confirmed'
    )
    add_scalebar(ax, region, location='lower left')
    ax.legend(loc='upper right', title='Stations', fontsize=10)
    return ax

def min_window_fixed(arrivals):
    arrivals = np.array(arrivals, dtype=float)
    N = len(arrivals)

    if N == 1:
        return arrivals[0]

    last = arrivals[-1]
    deltas = []

    for i in range(N-1):
        num = arrivals[i] - last
        denom = (N - 1 - i)

        # This gives a candidate Δ
        d = num / denom
        deltas.append(d)

    Δ_min = max([0] + deltas)  # Δ cannot be negative

    W_min = (N - 1) * Δ_min + last
    return W_min

def fixed_spacing(arrivals, window_size):
    arrivals = np.array(arrivals, dtype=float)
    N = len(arrivals)

    if N == 1:
        return np.array([0.0])

    origins = np.linspace(0, window_size, N)

    if np.any(origins + arrivals > window_size):
        raise ValueError(
            "Window too small for fixed spacing. "
            "Minimum required window = %.3f" % min_window_fixed(arrivals)
        )

    return origins

def random_spacing(arrivals, window_size, rng=None):
    """
    Generate a valid random spacing scenario.
    Each origin[i] is sampled such that origin[i] + arrival[i] <= window_size.
    """
    arrivals = np.array(arrivals)
    if rng is None:
        rng = np.random.default_rng()

    max_arr = arrivals.max()
    if window_size < max_arr:
        raise ValueError(f"Window too small. Must be >= max arrival ({max_arr}).")

    # For each EQ, sample origin ∈ [0, window_size - arrival]
    origins = rng.uniform(0, window_size - arrivals)

    return origins

def synthetic_wavelet(t, t0, phase):
    """
    Very small ringing at onset, then fast decay.
    P: narrow, slightly more impulsive
    S: wider, softer
    """
    if phase == "P":
        sigma = 0.9
        freq = 10          # LOW frequency = small wiggle
        ring_amp = 0.1    # SMALL oscillation amplitude
    else:
        sigma = 1.8
        freq = 7           # even softer for S
        ring_amp = 0.18

    # Gaussian envelope
    envelope = np.exp(-0.5 * ((t - t0) / sigma)**2)

    # Very small, very fast-decaying wiggle
    carrier = ring_amp * np.sin(freq * (t - t0)) * np.exp(-3 * np.abs(t - t0))

    # Impulsive part = envelope itself
    pulse = envelope

    # Combine: mostly impulsive bump + a tiny wiggle on top near t0
    return pulse + carrier

def plot_window_times(
    arrivals,
    last_allowed_arrival,
    save_path,
    relative_per_event=False,
    p_color="orange",
    s_color="green",
    last_event_id= None,
    last_p_color="blue",
    last_s_color="cyan",
    phase_column="phase",
):
    """
    Plot arrival window times vs index.

    - P and S phases colored by p_color / s_color.
    - If highlight_last_event=True:
        Last event P phases use last_p_color (default red)
        Last event S phases use last_s_color (default black)
    - Supports relative per-event y indexing.
    - Draws a vertical threshold line.
    """

    df = arrivals.copy()

    # Relative per-event y axis
    if relative_per_event:
        df["y"] = df.groupby("event_id").cumcount()
    else:
        df["y"] = df.index

    # Base color (P/S)
    df["color"] = df[phase_column].map({
        "P": p_color,
        "S": s_color
    }).fillna("gray")

    # Highlight last event if enabled
    if last_event_id is not None:
        is_last = df["event_id"] == last_event_id

        # Override colors only for the last event
        df.loc[is_last & (df[phase_column] == "P"), "color"] = last_p_color
        df.loc[is_last & (df[phase_column] == "S"), "color"] = last_s_color

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(12, 7))

    ax.scatter(df["window_time"], df["y"], s=10, c=df["color"])


    # Threshold line
    ax.axvline(last_allowed_arrival, color="red", linestyle="--", linewidth=2)

    # Labels
    ax.set_xlabel("Window Time (s)")
    ax.set_ylabel("Relative Index per Event" if relative_per_event else "Index")
    ax.set_title("Arrival Window Times (Colored by Phase | Last Event Highlighted)")

    # Legend
    ax.scatter([], [], color=p_color, label="P phase")
    ax.scatter([], [], color=s_color, label="S phase")

    if last_event_id is not None:
        ax.scatter([], [], color=last_p_color, label="Last Event P")
        ax.scatter([], [], color=last_s_color, label="Last Event S")

    ax.legend(loc="upper left")


    # Save
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()


def seismic_impulse_peak(points, dt=0.001, freq=20, damping=5, phase='P'):
    t = np.arange(points) * dt
    
    if phase.upper() == 'P':
        gaussian = np.exp(- (t/0.002)**2 )
        decay = np.exp(-damping * t)
        f = freq * 2
    elif phase.upper() == 'S':
        gaussian = np.exp(- (t/0.01)**2 )
        decay = np.exp(-damping/3 * t)
        f = freq
    else:
        raise ValueError("phase must be 'P' or 'S'")

    wave = gaussian + np.sin(2*np.pi*f*t) * decay
    return wave

def create_seismic_trace(
        total_points=2000,
        wave_length=120,
        positions=None,
        colors=None,
        pad=20,
        dt=0.001,
        freq=30,
        damping=20,
        phase='P'
    ):
    """
    Create a synthetic seismic trace and return all components needed for plotting.

    Returns a dictionary:
        {
            "seismo": 1D array,
            "waves": list of (padded_start, padded_end, wave, pos, end, color)
        }
    """
    if positions is None:
        positions = [200, 600, 1200, 1700]
    if colors is None:
        colors = ['r', 'g', 'b', 'orange']

    seismo = np.zeros(total_points)
    waves = []

    for i, pos in enumerate(positions):

        # generate impulse
        wave = seismic_impulse_peak(
            wave_length, dt=dt, freq=freq, damping=damping, phase=phase
        )

        # insert wave
        end = min(pos + wave_length, total_points)
        seismo[pos:end] += wave[:end - pos]

        # padding region for coloring
        padded_start = max(0, pos - pad)
        padded_end = min(total_points, end + pad)

        # save info
        waves.append((padded_start, padded_end, wave, pos, end, colors[i]))

    return {
        "seismo": seismo,
        "waves": waves,
    }

def plot_seismic_stations(
        df,
        save_path,
        total_points=2000,
        wave_length=120,
        sr=100,        # NEW PARAMETER
        freq=30,
        damping=100,
        top_n=None,
        color_by_event=True
    ):
    
    import matplotlib.cm as cm

    dt = 1.0 / sr   # sampling interval in seconds
    
    df = df.drop_duplicates(subset=["station", "event_id", "phase"])

    if top_n is not None:
        station_counts = df["station"].value_counts()
        top_stations = station_counts.head(top_n).index
        df = df[df["station"].isin(top_stations)]

    stations = df["station"].unique()
    stations = np.sort(stations)

    # If coloring by event, create color map
    if color_by_event:
        unique_events = df["event_id"].unique()
        n_events = len(unique_events)
        cmap = cm.get_cmap("tab20", min(n_events, 20))
        event_colors = {ev: cmap(i % 20) for i, ev in enumerate(unique_events)}

    fig, ax = plt.subplots(figsize=(14, 8))

    trace_scale = 1.0  # vertical scaling

    for s_i, station in enumerate(stations):

        df_s = df[df["station"] == station]

        positions = df_s["window_sample"].astype(int).values
        phases    = df_s["phase"].values
        event_ids = df_s["event_id"].values

        # Decide colors
        if color_by_event:
            colors = [event_colors[eid] for eid in event_ids]
        else:
            colors = ["#007A33" if p == "P" else "#005BBB" for p in phases]

        trace = np.zeros(total_points)
        wave_infos = []

        for pos, phase, color in zip(positions, phases, colors):

            pos = int(pos)
            if pos < 0 or pos >= total_points:
                continue

            data = create_seismic_trace(
                total_points=total_points,
                wave_length=wave_length,
                positions=[pos],
                colors=[color],
                pad=0,
                dt=dt,
                freq=freq,
                damping=damping,
                phase=phase
            )

            trace += data["seismo"]

            for item in data["waves"]:
                wave_infos.append(item)

        # X axis in seconds
        x_sec = np.arange(total_points) * dt

        # # full trace 
        # # ax.plot( # x_sec, # trace * trace_scale + s_i,
        #  # color="black", # linewidth=1 # )

        # Plot colored segments
        for padded_start, padded_end, wave, pos, end, color in wave_infos:
            x = np.arange(padded_start, padded_end) * dt
            y = np.zeros_like(x, dtype=float)

            inner_start = max(0, pos - padded_start)
            inner_end = inner_start + (end - pos)

            y[inner_start:inner_end] = wave[:inner_end - inner_start]

            ax.plot(
                x, y * trace_scale + s_i,
                color=color,
                linewidth=1.5
            )

    ax.set_yticks(range(len(stations)))
    ax.set_yticklabels([])

    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Station")
    ax.set_title("Synthetic Seismic Signals per Station")
    ax.set_xlim(0, total_points * dt)
    ax.set_ylim(-1, len(stations))

    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()

class EQWindow:
    def __init__(self, stations, 
                length=None,
                first_event_w=0.05, #percentage from 0 to 1 of the length
                last_event_w=0.05, #percentage from 0 to 1 of the length
                event_spacing="fixed", #fixed, random, free
                min_n_phase=5,  
                event_order="time"):

        self.length = length  # total window length in seconds
        self.first_event_w = first_event_w
        self.last_event_w = last_event_w
        self.event_spacing = event_spacing  # "fixed" or "random" or "free"
        self.min_n_phase = min_n_phase
        self.event_order = event_order  # "time" or "random" or column name

        self.event_origins = pd.DataFrame()
        self.arrivals = pd.DataFrame()

        self.stations = stations  # DataFrame with station info

        if self.first_event_w < 0 or self.last_event_w < 0 or self.first_event_w + self.last_event_w >=1:
            raise ValueError("first_event_w and last_event_w must be >=0 and their sum < 1")

        if 'latitude' not in stations.columns or 'longitude' not in stations.columns:
            raise ValueError(f"Columns 'latitude' or 'longitude' not found in stations dataframe")

    def sort_events(self,subset ="time"):
        if self.event_origins.empty:
            return

        self.event_origins.sort_values(subset, inplace=True)
        self.random_order = False

    def randomize_events(self):
        """
        Randomly shuffle the rows of the event_origins DataFrame.

        Notes
        -----
        - If `event_origins` is empty, the method returns immediately.
        - `sample(frac=1)` returns all rows in random order.
        - `reset_index(drop=True)` removes the old index and assigns a new one.
        """
        if self.event_origins.empty:
            return
        self.event_origins = self.event_origins.sample(frac=1).reset_index(drop=True)

    def _update_timeline(self):

        if self.event_origins.empty:
            return

        events = self.event_origins.copy()
        

        n_events = len(events)
        if n_events == 0:
            return

        if self.event_order == None:
            events.reset_index(drop=True, inplace=True)  # keep original order
        elif self.event_order == "random":
            events = events.sample(frac=1).reset_index(drop=True)
        else:
            try:
                events = events.sort_values(by=self.event_order).reset_index(drop=True)
            except KeyError:
                raise ValueError(f"Invalid event_order: {self.event_order}.")
        
        #add a new column with the time of the Nth arrival per event
        arrivals = self.arrivals.copy()
        min_phase = int(self.min_n_phase)
        
        nth_tt = get_nth_arrival_time(arrivals, n=min_phase,column="travel_time")
        
        nth_tt_per_ev = events["event_id"].map(nth_tt).to_numpy()

        max_nth_tt = np.nanmax(nth_tt_per_ev)
        # max_last_nth_tt = np.nanmax(last_nth_tt_per_ev)

        if self.length is not None:
            w = self.length
        else:
            w = 2*max_nth_tt
            self.length = w

        # ev_w = w - 3*w/4
        ev_w = w - self.last_event_w

        ev_w_start_pad = np.random.uniform(0,w * self.first_event_w)
        ev_w_end_pad = np.random.uniform(0,w * self.last_event_w)

        if self.event_spacing == "fixed":
            ev_times = np.linspace(ev_w_start_pad, ev_w, n_events, endpoint=True)
        elif self.event_spacing == "random":
            ev_times = np.sort(np.random.uniform(ev_w_start_pad, ev_w, n_events))
        elif self.event_spacing == "free":
            ev_times = np.array(nth_tt_per_ev)
        else:
            raise ValueError("event_spacing must be 'fixed', 'random', or 'free'")


        events["window_time"] = ev_times
        
        arrivals["origin_window_time"] = arrivals["event_id"].map(events.set_index("event_id")["window_time"])
        arrivals["window_time"] = arrivals["origin_window_time"] + arrivals["travel_time"]


        last_allowed_arrival = ev_times + nth_tt_per_ev
        max_last_allowed_arrival = np.nanmax(last_allowed_arrival)
        window_end = max_last_allowed_arrival + ev_w_end_pad

        path ="/groups/igonin/ecastillo/UTDQuake/utdquake/utils/window_debug.png"
        plot_window_times(arrivals, 
                            # max_last_allowed_arrival, 
                            window_end, 
                           relative_per_event=True,
                           last_event_id=events["event_id"].iloc[-1],
                            save_path=path)

        arrivals = arrivals[arrivals["window_time"] <= window_end].reset_index(drop=True)

        # print("ev_times:", ev_times)
        # print("max_last_allowed_arrival:", max_last_allowed_arrival)
        # print("nth_tt_per_ev:",nth_tt_per_ev)

        if not arrivals.empty:
            # Merge stations into arrivals, keeping existing columns clean
            arrivals = arrivals.merge(
                self.stations[["station", "latitude", 
                                "longitude","elevation"]],
                on="station",
                how="left"
            )

            # Warn if any arrival has no latitude or longitude
            missing_coords = arrivals[
                arrivals["latitude"].isna() | arrivals["longitude"].isna()
            ]

            if not missing_coords.empty:
                missing_stations = missing_coords["station"].unique()
                print(
                    f"Warning: Missing latitude/longitude for stations: {list(missing_stations)}"
                )
        
        self.event_origins = events
        self.arrivals = arrivals

    def add_events(self, events):
        if not isinstance(events, (list, tuple)):
            events = [events]

        cat = obspy.Catalog(events=events)

        if len(cat) == 0:
            #warning
            print("Warning: No events to add.")
            return

        origins_df = get_preferred_origins(cat)
        self.event_origins = pd.concat([self.event_origins, origins_df], 
                                        ignore_index=True)

        arrivals_df = cat.arrivals_to_df()

        events_df = self.event_origins[["preferred_origin_id", 
                                "event_id"]].copy()
        # events_df.rename(columns={"time":"origin_time"}, inplace=True)

        arrivals_df = arrivals_df.merge(
            events_df,
            left_on="origin_id",
            right_on="preferred_origin_id",
            how="left",
        )

        # m5 = origins_df[origins_df["magnitude"] >= 5]["event_id"].unique()
        # arrivals_m5 = arrivals_df[arrivals_df["event_id"].isin(m5)]
        # print(m5)
        # print(len(arrivals_m5))

        

        picks_df = cat.picks_to_df()
        merged = merge_arrivals_and_picks(arrivals_df, picks_df)
        merged["travel_time"] = (
                    merged["time"] - merged["origin_time"]
                ).dt.total_seconds()
        

        self.arrivals = pd.concat([self.arrivals, merged], ignore_index=True)
        # arrivals_m5 = self.arrivals[self.arrivals["event_id"].isin(m5)]
        # print(len(arrivals_m5))
        # exit()
        self._update_timeline()

    def add_stations(self, stations):
        """
        """
        if 'latitude' not in stations.columns or 'longitude' not in stations.columns:
            raise ValueError(f"Columns 'latitude' or 'longitude' not found in stations dataframe")
        
        self.stations = pd.concat([self.stations, stations], ignore_index=True)

    def add_noise(self,random_range=(1, 500)):
        n_phases = random.randint(*random_range)

        noise = self.stations
        sta_in_window = self.arrivals["station"].unique()
        noise["weight"] = noise.apply(lambda x: 1 if x["station"] in sta_in_window else 0.05, axis=1)
        noise = noise.sample(n_phases, weights="weight", replace=True,ignore_index=True) 


        random_floats = [random.uniform(0, self.length+self.length * self.last_event_w) for _ in range(len(noise))]
        random_phases = np.random.choice(['P', 'S'], size=len(noise))

        noise["window_time"] = random_floats
        noise["phase"] = random_phases
        noise["author"] = "noise"

        noise = noise[["author","station", "window_time", "phase", "latitude", "longitude", "elevation"]]

        # print(noise)
        self.arrivals = pd.concat([self.arrivals, noise], ignore_index=True)

        # print(self.arrivals[self.arrivals["author"] == "noise"][["station", "window_time", "phase", "latitude", "longitude", "elevation"]])
        # print(self.arrivals[self.arrivals["author"] == "noise"])
        # exit()
        # self.arrivals = pd.concat([self.arrivals, noise], ignore_index=True)

    def plot_window(self,
                    reference_location=None,
                    show_earthquakes=True,
                    show_earthquake_lines=True,
                    show_phases="both",
                    show_moveout=True,
                    show_station_labels=True,
                    
                    show_legend=True,
                    save_path=None,
                    ax=None,
                    show=True):

        if self.arrivals.empty or self.event_origins.empty:
            print("No events or arrivals to plot.")
            return

        if self.stations.empty:
            raise ValueError(
                "Station coordinates not found. Please use eqw.add_stations() before plotting."
            )

        stations = self.stations
        arrivals = self.arrivals.copy()
        earthquakes = self.event_origins

        # ------------------------------------------------------
        # 1. Determine reference mode
        # ------------------------------------------------------
        if reference_location is None:
            local_reference = True
        else:
            local_reference = False
            ref_lat, ref_lon, ref_elv = reference_location

        # GLOBAL reference only used if reference_location is not None
        if not local_reference:
            arrivals["y"] = arrivals.apply(
                lambda row: gps2dist_azimuth(
                    ref_lat, ref_lon, row["latitude"], row["longitude"]
                )[0] / 1000,
                axis=1,
            )
        else:
            arrivals["y"] = np.nan  # filled per event

        # Clean NaN coordinates
        nan_coords = arrivals[arrivals["latitude"].isna() | arrivals["longitude"].isna()]
        if not nan_coords.empty:
            missing_stations = nan_coords["station"].unique()
            print(f"Warning: Missing latitude/longitude for stations: {list(missing_stations)}")

        arrivals = arrivals.dropna(subset=["latitude", "longitude"], ignore_index=True)

        event_ids = earthquakes.sort_values("window_time")
        event_ids =event_ids["event_id"].unique()
        phase_mask = {"P": ["P"], "S": ["S"], "both": ["P", "S"]}[show_phases]

        colors = plt.cm.tab20c(np.linspace(0, 1, len(event_ids)))
        color_map = dict(zip(event_ids, colors))

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 4))

        # ------------------------------------------------------
        # 2. Event loop
        # ------------------------------------------------------
        arrivals_noise = arrivals[arrivals["author"] == "noise"]
        # Plot noise arrivals
        


        max_y = []
        
        for e, event_id in enumerate(event_ids, 1):

            # Event origin time
            event_start = earthquakes.loc[earthquakes["event_id"] == event_id, "window_time"].values[0]
            arrivals_event = arrivals[arrivals["event_id"] == event_id].copy()

            arrivals_event = arrivals_event[arrivals_event["author"] != "noise"]

            # Earthquake info
            eq = earthquakes[earthquakes["event_id"] == event_id].iloc[0]
            eq_lat = eq["latitude"]
            eq_lon = eq["longitude"]

            # --------------------------------------------------
            # Reference handling
            # --------------------------------------------------
            if local_reference:
                # Earthquake itself is reference → y_eq = 0
                y_eq = 0
                arrivals_event["y"] = arrivals_event.apply(
                    lambda row: gps2dist_azimuth(
                        eq_lat, eq_lon, row["latitude"], row["longitude"]
                    )[0] / 1000,
                    axis=1,
                )
            else:
                # Global reference already computed earlier
                y_eq = gps2dist_azimuth(
                    ref_lat, ref_lon, eq_lat, eq_lon
                )[0] / 1000

            print(f"Event #{e}: M{eq['magnitude']}-{eq['time']}. t={event_start} s, y={y_eq:.2f} km")
            
            # color = color_map[event_id]

            # check if e is even or odd for color selection
            if e % 2 == 0:
                color = "#ec7524"  # orange
            else:
                color = "#007A33"  # green


            # --------------------------------------------------
            # 3. Plot earthquake star
            # --------------------------------------------------
            if show_earthquakes:
                ax.scatter(event_start, y_eq, marker="*",alpha=0.5,
                                    color=color, s=100, zorder=5)
                
                #plot vertical line from earthquake to bottom
                

            # --------------------------------------------------
            # 4. Plot arrivals
            # --------------------------------------------------
            moveout_lines = {}
            for phase in phase_mask:
                arrivals_phase = arrivals_event[arrivals_event["phase"] == phase].copy()
                if arrivals_phase.empty:
                    continue

                # x-position (moveout line)

                
                arrivals_phase["x"] = arrivals_phase["window_time"]

                # arrivals_phase = arrivals_phase[arrivals_phase["x"] <= event_start + self.length]

                # if phase == "P":
                    # color_arrival = "#ec7524"
                    
                # else:
                    # color_arrival = "#007A33"    

                color_arrival = color

                if show_moveout:
                    # Draw moveout line from earthquake to each arrival
                    how="interp"

                    _x = arrivals_phase["x"]
                    _y = arrivals_phase["y"]
                    _x = np.append(_x, event_start)
                    _y = np.append(_y, y_eq)

                    if how == "linear":
                        #add 0 point at event origin
                        slope, intercept, r_value, _, _ = linregress(_x, _y)

                        x_moveout = np.linspace(event_start, _x.max(), 100)
                        y_moveout = slope * (x_moveout - event_start) + y_eq
                    else:
                        sort_idx = np.argsort(_x)
                        _x_sorted = _x[sort_idx]
                        _y_sorted = _y[sort_idx]
                        x_moveout = np.linspace(event_start, _x.max(), 100)
                        y_moveout = np.interp(x_moveout, _x_sorted, _y_sorted)


                    moveout_lines[phase] = (x_moveout, y_moveout)
                    
                    ax.plot(x_moveout, y_moveout, linestyle="--", color=color,
                            linewidth=0.8,
                                alpha=0.5, zorder=1)




                for _, row in arrivals_phase.iterrows():
                    facecolor = color if row["phase"] == "P" else "none"
                    # facecolor = color_arrival
                    edgecolor = color_arrival
                    ax.scatter(
                        row["x"], row["y"], marker="o",
                        facecolors=facecolor, edgecolors=edgecolor, 
                        s=10,
                        zorder=10
                    )
                # print(arrivals_phase[["station", "phase", "x", "y"]])
                max_y.append(arrivals_phase["y"].max())

            if "P" in moveout_lines and "S" in moveout_lines:
                xP, yP = moveout_lines["P"]
                xS, yS = moveout_lines["S"]

                # Common x-range
                xmin = max(xP.min(), xS.min())
                xmax = min(xP.max(), xS.max())

                if xmin < xmax:  # ensure overlap exists
                    # Build one shared x grid
                    x_common = np.linspace(xmin, xmax, 200)

                    # Interpolate both curves onto the shared grid
                    yP_common = np.interp(x_common, xP, yP)
                    yS_common = np.interp(x_common, xS, yS)

                    # Fill the area
                    ax.fill_between(
                        x_common,
                        yP_common,
                        yS_common,
                        color=color,
                        alpha=0.1,
                        zorder=0
                    )
            # --------------------------------------------------
            # 5. Station labels
            # --------------------------------------------------
            if show_station_labels:
                arrivals_plot = arrivals_event[arrivals_event["phase"].isin(phase_mask)].copy()
                arrivals_plot["x"] = event_start + (
                    arrivals_plot["time"] - arrivals_plot["origin_time"]
                ).dt.total_seconds()

                for (net, sta), group in arrivals_plot.groupby(["network", "station"]):
                    if "P" in group["phase"].values:
                        row_label = group[group["phase"] == "P"].iloc[0]
                        x_offset = -5
                        ha = "right"
                    else:
                        row_label = group.iloc[0]
                        x_offset = 5
                        ha = "left"

                    ax.text(
                        row_label["x"] + x_offset, row_label["y"], sta,
                        verticalalignment="center", horizontalalignment=ha,
                        fontsize=9, color=color
                    )
        
        max_distance = max(max_y)
        y_noise = np.random.uniform(0, max_distance, 
                                    size=len(arrivals_noise))
        if not arrivals_noise.empty:
            ax.scatter(
                    arrivals_noise["window_time"], y_noise,
                        marker="o",
                        alpha=0.5,
                    facecolors="gray",  s=10,
                    zorder = 0
                )
            
        y_min, y_max = ax.get_ylim()
            
        if show_earthquake_lines:
            for e, event_id in enumerate(event_ids, 1):

                eq = earthquakes[earthquakes["event_id"] == event_id].iloc[0]
                event_start = eq["window_time"]
                magnitude = eq["magnitude"]
                origin_time = eq["time"]

                # Draw main vertical line
                ax.plot([event_start, event_start], [0, y_max],
                        color="gray", alpha=0.5, linewidth=1.6, zorder=1)

        ax.set_ylim(y_min, y_max)

        if show_legend:
            legend_elements = [
                    Line2D([0], [0], marker='o', color='gray', label='Noise', 
                        markerfacecolor='gray', markersize=8, linestyle='None'),
                    Line2D([0], [0], marker='o', color='#007A33', label='P', 
                        markerfacecolor='#007A33', markersize=8, linestyle='None'),
                    Line2D([0], [0], marker='o', color='#007A33', label='S', 
                        markerfacecolor="none", markersize=8, linestyle='None'),
                    Line2D([0], [0], marker='*', color="#ec7524", label='Earthquake', 
                        markerfacecolor="#ec7524", markersize=12, linestyle='None')
                ]

            ax.legend(handles=legend_elements, loc='lower left', framealpha=0.9)


        # ax.set_xlim(0, self.max_length)
        # ax.set_ylim(-10, max(max_y) + 5)
        #inver  axis
        ax.invert_yaxis()
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position("top")

        ax.set_xlabel("Window time [s]")
        # ax.set_xlabel("Window time [s]", loc="left")
        ax.set_ylabel("Distance [km]")
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300)
        if show:
            plt.show()
        # else:
        #     plt.close(fig)
        
        return ax




if __name__ == "__main__":
    events = pd.read_csv('sgc.csv', comment='#')
    stations = events.sample(n=10, random_state=42)  # Sample 10 stations for visualization
    # region = [-80, -70, 0, 10]  # [min_lon, max_lon, min_lat, max_lat]
    region = [-75, -70, 0, 3]  # [min_lon, max_lon, min_lat, max_lat]
    # region = [-180, 180, -90, 90]  # [min_lon, max_lon, min_lat, max_lat]
    analysis = {
        'Contributor': 'Emmanuel Castillo',
        'events_total': len(events['time_event'].unique()), 
        'stations_good': len(events['station'].unique()),
        'stations_bad': 0,  # Placeholder for bad stations
        'p_arrivals_total': events['pick_p'].notnull().sum(),
        's_arrivals_total': events['pick_s'].notnull().sum()
    }
    output_file = 'output.png'
    plot_network_map(events, stations, region, analysis)