import matplotlib.pyplot as plt
import numpy as np

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

def plot_network_map_stats(events, stations, region, analysis, 
                output_file=None, show=True, alaska=False):
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
        'contributor', 'events_total', 'stations_good', 'stations_bad',
        'p_arrivals_total', 's_arrivals_total'.
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
    
    print(events.describe())

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


    ax1.set_title(f"Contributor: {analysis.get('contributor', 'N/A')}",
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


    if alaska:
        proj = ccrs.PlateCarree()
        region = [-180, -130, 49, 65]
    else:
        proj = ccrs.PlateCarree()

    ax2 = fig.add_subplot(gs[1, 0],
                        projection=proj
                    )
    
    ax2.set_extent(region, crs=proj)
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

    # ax2.set_title(f"Contributor: {analysis.get('contributor', 'N/A')}",
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

    return fig

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
        'contributor', 'events_total', 'stations_good', 'stations_bad',
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

    ax5.set_title(f"Contributor: {analysis.get('contributor', 'N/A')}",
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
        'contributor', 'events_total', 'stations_good', 'stations_bad',
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

    ax5.set_title(f"Contributor: {analysis.get('contributor', 'N/A')}",
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

def plot_seismic_overview(events,picks, savepath=None):
    """
    Create a 5-panel seismic overview figure:
    - Time series of events
    - Depth histogram
    - Magnitude histogram
    - Epicentral distance distribution
    - Azimuth distribution
    
    Parameters
    ----------
    events : pandas.DataFrame
        DataFrame with columns: ['time', 'depth', 'magnitude', 
                                 'epicentral_distance', 'azimuth']
    savepath : str or None, optional
        If provided, saves the figure to this path with dpi=300.
        If None, just returns fig and axes without saving.
    
    Returns
    -------
    fig : matplotlib.figure.Figure
    axes : dict of matplotlib.axes.Axes
        Dictionary of axes with keys: 'time', 'depth', 'magnitude', 
        'epicentral_distance', 'azimuth'
    """
    
    # Create figure
    fig = plt.figure(figsize=(10, 8))

    # # Define grid layout: 3 rows × 2 columns
    # gs = gridspec.GridSpec(2, 2, width_ratios=[1, 1], 
    #                         height_ratios=[1, 1], figure=fig)
    # Define grid layout: 3 rows × 2 columns
    gs = gridspec.GridSpec(2, 4, figure=fig)

    # Left column plots (stacked 3)
    # ax1 = fig.add_subplot(gs[0, 0])  # Time
    # ax2 = fig.add_subplot(gs[1, 0])  # Depth
    # ax3 = fig.add_subplot(gs[0, 1])  # Distance
    # ax4 = fig.add_subplot(gs[1, 1], projection="polar")  # azimuth

    ax1 = fig.add_subplot(gs[0, 0:2])  # Time
    ax2 = fig.add_subplot(gs[0, 2:4])  # Depth
    ax3 = fig.add_subplot(gs[1, 1:3])  # Distance
    ax4 = fig.add_subplot(gs[1, 0], projection="polar")  # azimuth
    ax5 = fig.add_subplot(gs[1, 3], projection="polar")  # New centered plot spanning both columns
    
    # Labels
    # Example: add subplot labels (a, b, c, d, e)
    axes = [ax1, ax2, ax4,ax3, ax5]
    labels = ['(a)', '(b)', '(c)', '(d)','(e)']
    for ax, label in zip(axes, labels):
        ax.text(-0.1, 1.05, label, transform=ax.transAxes,
                fontsize=12, 
                fontweight='bold',
                  va='bottom', ha='right')

    # --- Plotting ---
    # (a) Time series
    # events.groupby(events['time'].dt.to_period('M')).size().plot(ax=ax1)
    # ax1.set_title("Time")
    # ax1.set_ylabel("Count")

    # (b) Depth histogram
    depth_km = events['depth'].dropna() / 1e3

    # Compute limits
    lower, upper = np.percentile(depth_km, [1, 97])
    # Keep only the "central" data
    depth_filtered = depth_km[(depth_km >= lower) &\
                                (depth_km <= upper)]


    # Depth histogram
    ax1.hist(depth_filtered, bins=20, color='#006400', alpha=0.7)
    ax1.yaxis.set_major_formatter(FuncFormatter(human_format))
    ax1.set_xlabel('Depth [km]')
    ax1.set_ylabel('Counts')
    # ax2.yaxis.tick_right()
    # ax2.yaxis.set_label_position("right")
    ax1.set_yscale("log")
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.set_title("Depth")

    # formatter = mticker.ScalarFormatter()
    # formatter.set_scientific(True)
    # formatter.set_powerlimits((0, 0)) 
    # ax4.yaxis.set_major_formatter(formatter)
    # ax2.hist(events['depth'], bins=40, color='steelblue')
    # ax2.set_yscale("log")
    # ax2.set_title("Depth")
    # ax2.set_xlabel("Depth [km]")
    # ax2.set_ylabel("Log Frequency")

    # (c) Magnitude histogram
    ax2.hist(events['magnitude'], bins=40, 
            #  color='slateblue'
             color='#ec7524'
             )
    ax2.set_yscale("log")
    ax2.set_title("Magnitude")
    ax2.set_xlabel("Magnitude")
    ax2.set_ylabel("Log Frequency")

    # Annotate max/min magnitude
    max_mag, min_mag = events['magnitude'].max(), events['magnitude'].min()
    ax2.annotate(f"Max: {max_mag:.2f} M", xy=(0.98, 0.95),
                 xycoords="axes fraction", ha="right", fontsize=9)
    ax2.annotate(f"Min: {min_mag:.2f} M", xy=(0.98, 0.88),
                 xycoords="axes fraction", ha="right", fontsize=9)

    # # (d) Epicentral distance (pie chart)
    bins = [0,  30, 60, 100, 150, 200, 300,  np.inf]  # include >500 km
    labels_dist = [
                        f">{int(bins[i])} km" if bins[i+1] == np.inf 
                        else f"{int(bins[i])}-{int(bins[i+1])} km"
                        for i in range(len(bins)-1)
                    ]

    # Compute counts per bin
    picks["distance_km"] = picks['distance'] * 111  # make sure 'distance' column exists
    counts, _ = np.histogram(picks["distance_km"], bins=bins)

    print(counts)

    # Use YlGn colormap with discrete colors
    n_bins = len(counts)
    cmap = cm.get_cmap("YlGn", n_bins)
    colors_discrete = [cmap(i) for i in range(n_bins)]

    # Assign colors so that the highest count gets the darkest color
    sorted_indices = np.argsort(counts)[::-1]  # indices of counts in descending order
    colors = [None] * n_bins
    for color, idx in zip(colors_discrete[::-1], sorted_indices):  # darkest color first
        colors[idx] = color

    alpha = 0.7  # between 0 (transparent) and 1 (opaque)
    colors_with_alpha = [(r, g, b, alpha) for r, g, b, _ in colors]
    ax3.pie(counts, labels=labels_dist, autopct='%1.0f%%', colors=colors_with_alpha, startangle=90)
    ax3.set_title("Epicentral Distance")

    # for text in autotexts:
    #     text.set_color('white')

    # # (e) Azimuth 
    bins = 12
    azimuth_rad = np.deg2rad(events["azimuthal_gap"].values)

    counts, bin_edges = np.histogram(azimuth_rad, bins=bins, range=(0, 2*np.pi))
    angles = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Convert counts to percentage
    percentages = 100 * counts / counts.sum()

    cmap = create_green_to_orange_cmap(n_colors=bins)
    norm = mcolors.Normalize(vmin=percentages.min(), vmax=percentages.max())
    colors = cmap(norm(percentages))

    alpha = 0.7  # 0 = fully transparent, 1 = fully opaque
    colors = [(r, g, b, alpha) for r, g, b, _ in colors]

    # Plot bars with colors
    bars = ax4.bar(angles, np.ones_like(counts), 
                   width=2*np.pi/bins, bottom=0,
                  align="center", 
                  edgecolor="k", 
                  color=colors)

    ax4.plot(0, 0, marker="*", color="black", markersize=18, zorder=5)
    sep = 30  # degrees
    label_angles = np.deg2rad(np.arange(0, 360, sep))

    # # Place triangles just inside the edge (below the tick labels)
    # r_station = 1.05  # slightly outside your bars
    # ax4.scatter(label_angles, np.full_like(label_angles, r_station),
    #             marker="^", color="black", s=80, zorder=6)

    # Format
    ax4.set_theta_zero_location("N")   # 0° at top
    ax4.set_theta_direction(-1)        # clockwise
    ax4.set_yticklabels([])   # remove radial tick labels
    ax4.set_yticks([])        # remove tick marks too (optional)
    ax4.set_thetagrids(np.arange(0, 360, sep))  # ticks every 30°
    ax4.set_title("Azimuthal gap", pad=25)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cax = inset_axes(ax4, width="60%", height="5%", 
                     loc="lower center",
                     borderpad=-3)  # tweak position/size
    cbar = plt.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.set_label("Percentage [%]")

    # ax.set_title("Azimuth Histogram (Rose Diagram)", va="bottom")
    # bins = [0, 90, 180, 270, 360]
    # labels_az = [f"{bins[i]}-{bins[i+1]}°" for i in range(len(bins)-1)]
    # counts, _ = np.histogram(picks['azimuth'], bins=bins)
    # ax5.pie(counts, labels=labels_az, autopct='%1.0f%%')
    # ax5.set_title("Azimuths")

    bins = 12
    azimuth_rad = np.deg2rad(picks["azimuth"].values)

    counts, bin_edges = np.histogram(azimuth_rad, bins=bins, range=(0, 2*np.pi))
    angles = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Convert counts to percentage
    percentages = 100 * counts / counts.sum()

    cmap = create_green_to_orange_cmap(n_colors=bins)
    norm = mcolors.Normalize(vmin=percentages.min(), vmax=percentages.max())
    colors = cmap(norm(percentages))

    alpha = 0.7  # 0 = fully transparent, 1 = fully opaque
    colors = [(r, g, b, alpha) for r, g, b, _ in colors]

    # Plot bars with colors
    bars = ax5.bar(angles, np.ones_like(counts), 
                   width=2*np.pi/bins, bottom=0,
                  align="center", 
                  edgecolor="k", 
                  color=colors)

    ax5.plot(0, 0, marker="*", color="black", markersize=18, zorder=5)
    sep = 30  # degrees
    label_angles = np.deg2rad(np.arange(0, 360, sep))

    # Place triangles just inside the edge (below the tick labels)
    r_station = 1.05  # slightly outside your bars
    ax5.scatter(label_angles, np.full_like(label_angles, r_station),
                marker="^", color="black", s=80, zorder=6)

    # Format
    ax5.set_theta_zero_location("N")   # 0° at top
    ax5.set_theta_direction(-1)        # clockwise
    ax5.set_yticklabels([])   # remove radial tick labels
    ax5.set_yticks([])        # remove tick marks too (optional)
    ax5.set_thetagrids(np.arange(0, 360, sep))  # ticks every 30°
    ax5.set_title("Azimuth", pad=25)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cax = inset_axes(ax5, width="60%", height="5%", 
                     loc="lower center",
                     borderpad=-3)  # tweak position/size
    cbar = plt.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.set_label("Percentage [%]")


    plt.tight_layout()

    # Save or show
    if savepath:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")
    else:
        plt.show()

    # Return figure and axes dictionary
    axes_dict = {
        'time': ax1,
        'depth': ax2,
        'magnitude': ax3,
        'epicentral_distance': ax4,
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
        (first_p, "tt_first_P", "distance_km", "First P Arrivals", orange, orange),
        (last_p,  "tt_last_P",  "distance_km", "Last P Arrivals", orange, orange),
        (first_s, "tt_first_S", "distance_km", "First S Arrivals", orange, orange),
        (last_s,  "tt_last_S",  "distance_km", "Last S Arrivals", orange, orange),
        (first_sp, "tt_SP", "distance_km", "First S-P Picks", orange, orange),
        (last_sp,  "tt_SP", "distance_km", "Last S-P Picks", orange, orange),
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
            data=data, x=x, y=y, kind="hist", height=4,
            color=scatter_color,
            marginal_kws=dict(bins=20, fill=True, color=marginal_color),
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




if __name__ == "__main__":
    events = pd.read_csv('sgc.csv', comment='#')
    stations = events.sample(n=10, random_state=42)  # Sample 10 stations for visualization
    # region = [-80, -70, 0, 10]  # [min_lon, max_lon, min_lat, max_lat]
    region = [-75, -70, 0, 3]  # [min_lon, max_lon, min_lat, max_lat]
    # region = [-180, 180, -90, 90]  # [min_lon, max_lon, min_lat, max_lat]
    analysis = {
        'contributor': 'Emmanuel Castillo',
        'events_total': len(events['time_event'].unique()), 
        'stations_good': len(events['station'].unique()),
        'stations_bad': 0,  # Placeholder for bad stations
        'p_arrivals_total': events['pick_p'].notnull().sum(),
        's_arrivals_total': events['pick_s'].notnull().sum()
    }
    output_file = 'output.png'
    plot_network_map(events, stations, region, analysis)
    
