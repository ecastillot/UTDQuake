"""
plot.py  
(This can be improved significantly with more modularization later... I am a bit lazy to do it now)

Functions for plotting seismic data, including:

- Network and event overview maps (plot_overview, plot_utdq_overview)
- Seismic statistics and histograms (plot_stats, plot_pick_histograms)
- Uncertainty visualization (plot_uncertainty_boxplots)
- Utility functions like add_scalebar
- Multi-panel QC plot for multiple seismic phases.

Dependencies:
- numpy, pandas, matplotlib, seaborn, scipy
- cartopy (for geographic plotting)
- .utils (custom helpers: compute_region, human_format, etc.)

Author: Emmanuel David Castillo Taborda
Date: 2026-01-30
"""

# Core packages
import numpy as np
import pandas as pd
import tempfile
import os
import warnings
import string
from typing import Optional, Tuple, List, Dict, Any

# Matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import matplotlib.ticker as mticker
from matplotlib.ticker import FuncFormatter, MultipleLocator
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import matplotlib.image as mpimg
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset


# Seaborn
import seaborn as sns

# SciPy
from scipy.stats import linregress
from ..qc.config import GLOBAL_TRENDS_DEFAULTS_DEG2
from .utils import (compute_region, 
                    human_format, 
                    smart_date_formatter,
                    create_green_to_orange_cmap
                    )

def add_scalebar(
    ax: plt.Axes,
    region: Tuple[float, float, float, float],
    location: str = 'upper left'
) -> None:
    """
    Add a simple scale bar to a map.

    Parameters
    ----------
    ax : plt.Axes
        Axes to draw the scale bar on.
    region : tuple
        Map extent as (lon_min, lon_max, lat_min, lat_max).
    location : str, optional
        Location of the scale bar. Options: 'upper left', 'upper right',
        'lower left', 'lower right'. Default is 'upper left'.

    Returns
    -------
    None

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> region = (-70, -60, 2, 10)
    >>> add_scalebar(ax, region, location='lower left')
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

def plot_overview(
    events: pd.DataFrame,
    stations: pd.DataFrame,
    analysis: Dict[str, Any],
    consider_calculated_stations: bool=True,
    region: Optional[Tuple[float, float, float, float]] = None,
    is_alaska: bool = True,
    savepath: Optional[str] = None,
    show: bool = True
) -> None:
    """
    Plot a network overview with events, stations, and statistics.

    Parameters
    ----------
    events : pd.DataFrame
        Event table with columns: ['longitude', 'latitude', 'time', 'magnitude'].
    stations : pd.DataFrame
        Station table with columns: ['longitude', 'latitude', 'calculated', 'confirmed'].
    analysis : dict
        Dictionary with network statistics (events, stations, picks, etc.).
    consider_calculated_stations : bool, optional
        If True, also plot calculated stations (if available). Defaults to True.
    region : tuple, optional
        Map extent (lon_min, lon_max, lat_min, lat_max). Default: None.
    is_alaska : bool, optional
        If True, use a projection suitable for Alaska. Default: True.
    savepath : str, optional
        Path to save the figure. Default: None.
    show : bool, optional
        If True, display the figure. Default: True.

    Returns
    -------
    None

    Examples
    --------
    >>> plot_overview(df_events, df_stations, analysis_dict, region=(-70, -60, 2, 10))
    >>> plot_overview(df_events, df_stations, analysis_dict, savepath="overview.png", show=False)
    """
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
    except ImportError:
        raise ImportError("Cartopy is required for plot_overview")

    if region is None:
        calculated_stations = stations[stations["calculated"]==True]
        calculated_stations = calculated_stations.rename(columns={"calculated_longitude": "longitude",
                                                                "calculated_latitude": "latitude"})
        confirmed_stations = stations[stations["confirmed"]==True]
        confirmed_stations = confirmed_stations.rename(columns={"confirmed_longitude": "longitude",
                                                                "confirmed_latitude": "latitude"})
        if calculated_stations.empty and confirmed_stations.empty:
            raise ValueError("No stations found for region calculation.")
        elif calculated_stations.empty:
            all_stations = confirmed_stations
        elif confirmed_stations.empty:
            all_stations = calculated_stations
        else:
            all_stations = pd.concat([calculated_stations, confirmed_stations], ignore_index=True)

        all_stations = all_stations.drop_duplicates(subset=["network", "station"])
        region = compute_region(
                    events, all_stations, padding=0.2, 
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


    ax1.set_title(f"Contributor: {analysis.get('network', 'N/A')}",
                  fontsize=14, weight='bold',loc='left')
    print(analysis)
    print(analysis.get('located_stations', 'N/A'))
    ax1.text(
        0.70, 0.8,
        f"Events: {human_format(analysis.get('events', len(events)))}\n"
        f"Total Stations: {human_format(analysis.get('total_stations', 'N/A'))}\n"
        f" -Located: {human_format(analysis.get('located_stations', 'N/A'))}\n"
        f" --Confirmed: {human_format(analysis.get('confirmed_stations', 'N/A'))}\n"
        f"P Arrivals: {human_format(analysis.get('p_arrivals', 'N/A'))}\n"
        f"S Arrivals: {human_format(analysis.get('s_arrivals', 'N/A'))}",
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
        Line2D([0], [0], marker='^', color='w', label='Confirmed\nStations',
               markerfacecolor='green', markersize=8, markeredgecolor='green')
                ]
    if consider_calculated_stations and \
       'calculated_latitude' in stations.columns and \
       'calculated_longitude' in stations.columns:
        calc_label = Line2D([0], [0], marker='^', color='w', label='Calculated\nStations',
               markerfacecolor='gray', markersize=8, markeredgecolor='gray')
        legend_elements.append(calc_label)
        
    if len(legend_elements) ==3:
        bbox_anchor = (0.05, 0.9)
    else:
        bbox_anchor = (0.05, 0.7)

    ax1.legend(handles=legend_elements,
               loc='upper left',
            #    fontsize='x-small',
               bbox_to_anchor=bbox_anchor,
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

    # Mask for confirmed stations
    confirmed_mask = stations[['confirmed_longitude', 'confirmed_latitude']].notna().all(axis=1)
    # Plot calculated stations first (background layer)
    if consider_calculated_stations and \
       'calculated_latitude' in stations.columns and \
       'calculated_longitude' in stations.columns:
        calculated_mask = (~confirmed_mask) & stations[['calculated_longitude', 'calculated_latitude']].notna().all(axis=1)
        ax1.scatter(
            stations.loc[calculated_mask, 'calculated_longitude'],
            stations.loc[calculated_mask, 'calculated_latitude'],
            marker='^',
            c='gray',
            alpha=0.7,
            transform=ccrs.PlateCarree(),
            label='Calc. Stations'
        )

    ax1.scatter(
        stations.loc[confirmed_mask, 'confirmed_longitude'],
        stations.loc[confirmed_mask, 'confirmed_latitude'],
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
    # print(f"Start time: {starttime}, End time: {endtime}")
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
    if is_alaska:
        proj = ccrs.AlbersEqualArea(
                            central_longitude=-154,
                            central_latitude=50,
                            standard_parallels=(55, 65)
                        )
        region =(-180, -130, 50, 72)
    else:
        proj = ccrs.PlateCarree()


    ax2 = fig.add_subplot(gs[1, 0],
                        projection=proj
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

    if consider_calculated_stations and \
       'calculated_latitude' in stations.columns and \
       'calculated_longitude' in stations.columns:
        calculated_mask = (~confirmed_mask) & stations[['calculated_longitude', 'calculated_latitude']].notna().all(axis=1)
        ax2.scatter(
            stations.loc[calculated_mask, 'calculated_longitude'],
            stations.loc[calculated_mask, 'calculated_latitude'],
            marker='^',
            c='gray',
            alpha=1,
            transform=ccrs.PlateCarree(),
            label='Calc. Stations'
        )

    ax2.scatter(
        stations.loc[confirmed_mask, 'confirmed_longitude'],
        stations.loc[confirmed_mask, 'confirmed_latitude'],
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

    if savepath:
        plt.savefig(savepath, dpi=300)
        print(f"Saved plot to {savepath}")
    if show:
        plt.show()

    plt.close(fig)


def plot_utdq_overview(
    events: pd.DataFrame,
    stations: pd.DataFrame,
    analysis: Dict[str, Any],
    consider_calculated_stations: bool=True,
    region: Optional[Tuple[float, float, float, float]] = None,
    savepath: Optional[str] = None,
    show: bool = False,
) -> None:
    """
    Plot a two-panel map overview:
    - Top: Earthquake epicenters
    - Bottom: Seismic stations

    Parameters
    ----------
    events : pandas.DataFrame
        Must contain 'longitude' and 'latitude'.
    stations : pandas.DataFrame
        Must contain 'longitude' and 'latitude'.
    analysis : dict
        Summary statistics (events, arrivals, stations).
    consider_calculated_stations : bool, optional
        If True, also plot calculated stations (if available). Defaults to True.
    region : tuple or None, optional
        Map extent as (lon_min, lon_max, lat_min, lat_max).
        Defaults to global view.
    savepath : str, optional
        Output savepath.
    show : bool, optional
        If True, displays the figure.

    Returns
    -------
    output_path : str
        Full path to the saved figure.
    """

    try:
        import cartopy.crs as ccrs
    except ImportError:
        raise ImportError("Cartopy is required for plot_overview")

    region = (-180, 180, -90, 90) if region is None else region

    fig, (ax1, ax2) = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(12, 8),
        dpi=300,
        subplot_kw={'projection': ccrs.PlateCarree()},
        sharex=True
    )

    # ------------------ Earthquakes ------------------
    ax1, gl1 = setup_map(ax1, region)
    gl1.top_labels = True
    gl1.right_labels = False
    gl1.left_labels = True
    gl1.bottom_labels = False

    ax1.scatter(
        events['longitude'],
        events['latitude'],
        color="#ec7524",
        transform=ccrs.PlateCarree(),
        label="Earthquakes"
    )
    ax1.legend(loc="lower right", fontsize=12)

    ax1.text(
        0.02, 0.05,
        f"Events: {human_format(analysis.get('events', len(events)))}\n"
        f"P Arrivals: {human_format(analysis.get('p_arrivals', 'N/A'))}\n"
        f"S Arrivals: {human_format(analysis.get('s_arrivals', 'N/A'))}",
        transform=ax1.transAxes,
        ha="left",
        va="bottom",
        fontsize=12,
        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
    )

    # ------------------ Stations ------------------
    ax2, gl2 = setup_map(ax2, region)
    gl2.top_labels = False
    gl2.right_labels = False
    gl2.left_labels = True
    gl2.bottom_labels = True

    # Mask for confirmed stations (valid official coordinates)
    confirmed_mask = stations[['confirmed_longitude', 
                               'confirmed_latitude']].notna().all(axis=1)
    
    # Plot optional calculated stations first (background layer)
    if consider_calculated_stations and \
       'calculated_latitude' in stations.columns and \
       'calculated_longitude' in stations.columns:

        # Only plot rows where calculated values exist
        calculated_mask = (
                            ~confirmed_mask &
                            stations[['calculated_latitude', 
                                    'calculated_longitude']].notna().all(axis=1)
                        )
        
        ax2.scatter(
                    stations.loc[calculated_mask, 
                                 'calculated_longitude'],
                    stations.loc[calculated_mask, 
                                 'calculated_latitude'],
                    marker="^",
                    c="gray",
                    s=40,
                    alpha=0.6,
                    transform=ccrs.PlateCarree(),
                    label="Calc. Stations"
                )

    ax2.scatter(
        stations.loc[confirmed_mask, 'confirmed_longitude'],
        stations.loc[confirmed_mask, 'confirmed_latitude'],
        marker="^",
        c="green",
        s=40,
        alpha=0.7,
        transform=ccrs.PlateCarree(),
        label="Conf. Stations"
    )

    
    ax2.legend(loc="lower right", fontsize=12)

    ax2.text(
        0.02, 0.05,
        f"Stations: {human_format(analysis.get('total_stations', 'N/A'))}\n"
        f"-Located: {human_format(analysis.get('located_stations', 'N/A'))}\n"
        f"--Confirmed: {human_format(analysis.get('confirmed_stations', 'N/A'))}",
        transform=ax2.transAxes,
        ha="left",
        va="bottom",
        fontsize=12,
        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
    )

    # Layout + save
    plt.subplots_adjust(hspace=0.05)
    
    if savepath:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")
        print(f"Saved plot to {savepath}")
    if show:
        plt.show()

    plt.close(fig)



def plot_stats(
    events: pd.DataFrame,
    picks: Optional[pd.DataFrame] = None,
    savepath: Optional[str] = None,
    show: bool = True
) -> Tuple[plt.Figure, Dict[str, plt.Axes]]:
    """
    Plot a 5-panel figure with earthquake statistics.

    Panels include: depth, magnitude, epicentral distance, azimuthal gap, azimuth distribution.

    Parameters
    ----------
    events : pd.DataFrame
        Events table with columns: ['time', 'depth', 'magnitude', 'azimuthal_gap'].
    picks : pd.DataFrame, optional
        Picks table for distance and azimuth calculations. Default: None.
    savepath : str, optional
        Path to save the figure. Default: None.
    show : bool, optional
        If True, display the figure. Default: True.

    Returns
    -------
    fig : plt.Figure
        Figure object.
    axes_dict : dict
        Dictionary with axes for each subplot:
        {'depth', 'magnitude', 'epicentral_distance', 'azimuthal_gap', 'azimuth'}.

    Examples
    --------
    >>> fig, axes = plot_stats(df_events)
    >>> fig, axes = plot_stats(df_events, df_picks, savepath="stats.png", show=False)
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

    fig.tight_layout()

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

    if show:
        plt.show()
    
    plt.close(fig)

    axes_dict = {
        'depth': ax1,
        'magnitude': ax2,
        'epicentral_distance': ax3,
        'azimuthal_gap': ax4,
        'azimuth': ax5
    }
    return fig, axes_dict

def plot_uncertainty_boxplots(
    df: pd.DataFrame,
    figsize: Tuple[int, int] = (4, 6),
    dpi: int = 300,
    savepath: Optional[str] = None,
    show: bool = True
) -> Tuple[plt.Figure, list]:
    """
    Plot boxplots for horizontal, vertical uncertainties and standard error.

    Parameters
    ----------
    df : pd.DataFrame
        Must include columns: ['horizontal_uncertainty', 'vertical_uncertainty', 'standard_error'].
    figsize : tuple, optional
        Figure size. Default: (4, 6).
    dpi : int, optional
        Figure resolution. Default: 300.
    savepath : str, optional
        Path to save figure. Default: None.
    show : bool, optional
        If True, display the figure. Default: True.

    Returns
    -------
    fig : plt.Figure
        Figure object.
    axes : list
        List of axes objects.

    Examples
    --------
    >>> plot_uncertainty_boxplots(df)
    >>> plot_uncertainty_boxplots(df, savepath="uncertainty.png", show=False)
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

    if savepath:
        fig.savefig(savepath, dpi=dpi, bbox_inches="tight")
        print(f"Saved plot to {savepath}")
    if show:
        plt.show()

    plt.close(fig)

    return fig, axes


def plot_pick_histograms(
    df: pd.DataFrame,
    savepath: Optional[str] = None,
    show: bool = True
) -> Tuple[plt.Figure, list]:
    """
    Plot histograms of P picks, S picks, and Vp/Vs ratio (Wadati method).

    Parameters
    ----------
    df : pd.DataFrame
        Must include columns: ['phase', 'origin_id', 'origin_time', 'time', 'network', 'station'].
    savepath : str, optional
        Path to save the figure. Default: None.
    show : bool, optional
        If True, display the figure. Default: True.

    Returns
    -------
    fig : plt.Figure
        Figure object.
    axes : list
        List of axes objects.

    Examples
    --------
    >>> plot_pick_histograms(df_picks)
    >>> fig, axes = plot_pick_histograms(df_picks, savepath="pick_hist.png", show=False)
    """
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

        merged = merged.dropna(subset=['tt_P', 'tt_SP'])

        if len(merged) < 2 or merged.empty or\
            merged['tt_P'].nunique() < 2 or merged['tt_SP'].nunique() < 2:
            # print(f"No Vp/Vs calculation for origin {origin_id}. Not enough valid points for linear regression. ")
            warnings.warn(f"No Vp/Vs calculation for origin {origin_id}. Not enough valid points for linear regression. ")
            lr = None
            continue
        else:
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

    if savepath:
        plt.savefig(savepath, dpi=300)
        print(f"Saved plot to {savepath}")
    if show:
        plt.show()

    plt.close(fig)

    return fig, axes

def plot_pick_stats(df, distance_type="epicentral", savepath=None, show=True):
    """
    Plot summary statistics for seismic picks (P, S, and S-P) as jointplots.

    The function computes:
    - First and last P travel times per event.
    - First and last S travel times per event.
    - First and last S-P times for stations with both P and S picks.
    - Corresponding distances (either epicentral or hypocentral).

    It creates individual seaborn jointplots (scatter + marginal histograms),
    saves them temporarily as PNGs, and combines them into a single multi-panel
    matplotlib figure.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing pick information. Expected columns:
        - "origin_id"
        - "origin_time"
        - "time"
        - "phase"
        - "distance" (in degrees)
        - "linear_hyp_distance" (in km, optional)
        - "network"
        - "station"
    distance_type : str, default "epicentral"
        Which distance to use:
        - "epicentral": horizontal distance from epicenter (converted from degrees to km).
        - "hypocentral": approximate distance from hypocenter (linear approx.) (requires 'linear_hyp_distance').
    savepath : str or pathlib.Path, optional
        Path to save the final figure.
    show : bool, default True
        Whether to display the figure.

    Returns
    -------
    matplotlib.figure.Figure
        Combined multi-panel figure of all jointplots.
    """

    # Validate distance_type and compute 'distance_used'
    if distance_type == "epicentral":
        df["distance_used"] = df["distance"] * 111
        distance_label = "Epicentral Distance (km)"
    elif distance_type == "hypocentral":
        if "linear_hyp_distance" not in df.columns:
            raise ValueError(
                "DataFrame must contain 'linear_hyp_distance' for distance_type='hypocentral'"
            )
        df["distance_used"] = df["linear_hyp_distance"]
        distance_label = "Hypocentral Distance (km)"
    else:
        raise ValueError("distance_type must be 'epicentral' or 'hypocentral'")
    
    green = "#007A33"
    orange = "#ec7524"

    # remove nan with a logging warning
    if df[['time','origin_time']].isnull().any().any():
        how_many = df[['time','origin_time']].isnull().sum().sum()
        warnings.warn(f"{how_many} rows have NaN in 'time' or 'origin_time' and will be dropped for pick statistics.")
    
    df = df.dropna(subset=['time','origin_time'])


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
        s_group[['network', 'station', 'origin_id', 'distance_used', 'time']],
        p_group[['network', 'station', 'origin_id', 'distance_used', 'time']],
        on=['network', 'station', 'origin_id', 'distance_used'],
        suffixes=('_S', '_P')
    )
    common_stations = common_stations.drop_duplicates(subset=['network','station',"origin_id"])
    common_stations["tt_SP"] = (common_stations["time_S"] - common_stations["time_P"]).dt.total_seconds()

    first_sp = common_stations.sort_values('tt_SP').groupby('origin_id').first()
    last_sp  = common_stations.sort_values('tt_SP').groupby('origin_id').last()

    datasets = [
        (first_p, "tt_first_P", "distance_used", "First P Arrivals", orange, orange),
        (last_p,  "tt_last_P",  "distance_used", "Last P Arrivals", orange, orange),
        (first_s, "tt_first_S", "distance_used", "First S Arrivals", green, green),
        (last_s,  "tt_last_S",  "distance_used", "Last S Arrivals", green, green),
        (first_sp, "tt_SP", "distance_used", "First S-P Picks", "black", "black"),
        (last_sp,  "tt_SP", "distance_used", "Last S-P Picks", "black", "black"),
    ]

    labels = {"tt_first_P": "First P Arrival Time (s)",
              "tt_last_P": "Last P Arrival Time (s)",
              "tt_first_S": "First S Arrival Time (s)",
              "tt_last_S": "Last S Arrival Time (s)",
              "tt_SP": "S-P Time (s)",
              "distance_used": distance_label}

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

    if savepath:
        plt.savefig(savepath, dpi=300)
        print(f"Saved plot to {savepath}")

    if show:
        plt.show()

    plt.close(fig)

    # Clean up temporary files
    for f in temp_files:
        os.remove(f)

    # plt.show()
    return fig

def plot_station_location_uncertainty(
    df: pd.DataFrame,
    savepath: str,
    dpi: int = 300,
    show: bool = True
) -> None:
    """
    Plot and compare confirmed vs calculated station locations.

    This function visualizes the difference between confirmed and
    calculated station coordinates. It plots a scatter plot of
    confirmed coordinates and overlays calculated coordinates, allowing
    for quick inspection of station location accuracy.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain the following columns:
        - 'confirmed_latitude'
        - 'confirmed_longitude'
        - 'calculated_latitude'
        - 'calculated_longitude'
    savepath : str
        Path to save the resulting plot (e.g., 'station_uncertainty.png').
    dpi : int, optional
        Resolution of the saved figure. Default is 300.
    show : bool, optional
        If True, display the figure interactively. Default is True.

    Returns
    -------
    None

    Examples
    --------
    >>> plot_station_location_uncertainty(df_stations, "uncertainty.png", show=True)
    """
    try:
        import cartopy.crs as ccrs
    except ImportError:
        raise ImportError("Cartopy is required for plot_overview")
        
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
    if savepath is not None:
        fig.savefig(savepath, dpi=dpi)
        map_path = savepath.replace('.png','_map.png')
        fig2.savefig(map_path, dpi=dpi)
        print(f"Saved plot to {savepath}")
        print(f"Saved plot to {map_path}")
    
    if show:
        plt.show()

    plt.close(fig)
    
    # print(f"Mean total difference: {distance.mean():.4f} km")

def plot_venn(ax: "plt.Axes", df: pd.DataFrame) -> "plt.Axes":
    """
    Draw a Venn diagram comparing calculated and confirmed stations.

    This function visualizes the overlap between calculated and confirmed
    stations using a two-set Venn diagram. It highlights stations that are
    only calculated, only confirmed, and those present in both.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes object to draw the Venn diagram on.
    df : pandas.DataFrame
        DataFrame containing boolean or binary columns:
        - 'calculated': 1 if station is calculated, 0 otherwise
        - 'confirmed': 1 if station is confirmed, 0 otherwise

    Returns
    -------
    matplotlib.axes.Axes
        The axes object with the Venn diagram drawn.

    Raises
    ------
    ImportError
        If the `matplotlib-venn` library is not installed.

    Examples
    --------
    >>> fig, ax = plt.subplots()
    >>> plot_venn(ax, df_stations)
    >>> plt.show()
    """
    try:
        from matplotlib_venn import venn2
    except ImportError:
        raise ImportError("matplotlib-venn is required for plot_venn")

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

def setup_map(ax: "plt.Axes", region: list) -> tuple:
    """
    Configure a Cartopy map axis with standard geographic features.

    This function sets up a map with coastlines, borders, states, land, ocean,
    lakes, rivers, and gridlines. It also applies a geographic extent defined
    by the `region`.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The matplotlib axes object where the map will be drawn. Typically
        created using `plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})`.
    region : list
        Geographic extent of the map in the format [min_lon, max_lon, min_lat, max_lat].

    Returns
    -------
    tuple
        - ax : matplotlib.axes.Axes
            The configured axes with map features.
        - gl : cartopy.mpl.gridliner.Gridliner
            Gridliner object for further customization.

    Raises
    ------
    ImportError
        If the Cartopy library is not installed.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> import cartopy.crs as ccrs
    >>> fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
    >>> ax, gl = setup_map(ax, [-120, -70, 20, 50])
    >>> plt.show()
    """
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
    except ImportError:
        raise ImportError("Cartopy is required for setup_map")
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
    return ax, gl

def plot_station_map(ax: "plt.Axes", df: "pd.DataFrame", region: list) -> "plt.Axes":
    """
    Plot calculated and confirmed station locations on a geographic map.

    This function uses Cartopy to display station locations, distinguishing
    between stations that are only calculated and those that are both
    calculated and confirmed. It also adds a scale bar and a legend.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The matplotlib axes object where the map will be drawn.
    df : pandas.DataFrame
        DataFrame containing station information with at least the following columns:
        - 'network' : str, network code
        - 'station' : str, station code
        - 'confirmed' : int, 1 if station is confirmed, 0 otherwise
        - 'calculated' : int, 1 if station is calculated, 0 otherwise
        - 'confirmed_latitude', 'confirmed_longitude' : float, coordinates of confirmed stations
        - 'calculated_latitude', 'calculated_longitude' : float, coordinates of calculated stations
    region : list
        Geographic extent of the map in the format [min_lon, max_lon, min_lat, max_lat].

    Returns
    -------
    matplotlib.axes.Axes
        The axes object with the plotted station locations.

    Raises
    ------
    ImportError
        If Cartopy is not installed.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
    >>> ax = plot_station_map(ax, df_stations, [-120, -70, 20, 50])
    >>> plt.show()
    """
    try:
        import cartopy.crs as ccrs
    except ImportError:
        raise ImportError("Cartopy is required for setup_map")
    ax, gl = setup_map(ax, region)

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

def plot_network_station_density(
    df: pd.DataFrame,
    savepath: str = None,
    show: bool = False,
    dpi: int = 300
):
    """
    Plot network station count vs geographic extent with event-based marker sizes.
    Color points by continent.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain the following columns:
        - 'network': network name
        - 'approx_lon_min', 'approx_lon_max', 'approx_lat_min', 'approx_lat_max'
        - 'total_stations': number of stations in the network
        - 'events': number of events in the network
        - 'continent': continent of the network
    savepath : str, optional
        Path to save the figure. If None, figure is not saved.
    show : bool, optional
        If True, displays the figure.
    dpi : int, optional
        DPI for saving the figure. Default is 300.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The created figure object.
    ax : matplotlib.axes.Axes
        The created axes object.
    """
    df = df.copy()

    # Compute geographic ranges
    df["lon_range"] = df["approx_lon_max"] - df["approx_lon_min"]
    df["lat_range"] = df["approx_lat_max"] - df["approx_lat_min"]

    # Approximate area in square degrees
    df["area_deg2"] = df["lon_range"] * df["lat_range"]

    # Station and event densities (optional, not used for plotting here)
    df["station_density"] = df["total_stations"] / df["area_deg2"]
    df["event_density"] = df["events"] / df["area_deg2"]

    # Create figure and axes
    fig, ax = plt.subplots(figsize=(9, 7))

    # Scatter plot, colored by continent
    continents = df["continent"].unique()
    colors = plt.cm.tab10.colors  # Up to 10 colors
    continent_color_map = {cont: colors[i % len(colors)] for i, cont in enumerate(continents)}

    for cont in continents:
        subset = df[df["continent"] == cont]
        ax.scatter(
            subset["area_deg2"],
            subset["total_stations"],
            s=subset["events"] / 10,
            alpha=0.7,
            label=cont,
            color=continent_color_map[cont]
        )

    # Add network labels
    for i, net in enumerate(df["network"]):
        ax.text(
            df["area_deg2"][i],
            df["total_stations"][i],
            net,
            fontsize=8
        )

    # Log scales
    ax.set_xscale("log")
    ax.set_yscale("log")

    # Labels and title
    ax.set_xlabel("Network Area (deg²)")
    ax.set_ylabel("Total Stations")
    ax.set_title("Network Data Coverage")

    # Legend
    ax.legend(loc="upper left")

    # Grid
    ax.grid(True, which="both")

    # Layout
    plt.tight_layout()

    # Save figure if requested
    if savepath:
        fig.savefig(savepath, dpi=dpi, bbox_inches="tight")
        print(f"Saved plot to {savepath}")

    # Show figure if requested
    if show:
        plt.show()

    # Close figure to avoid memory issues
    plt.close(fig)

    return fig, ax

def plot_phase_count_radar_by_magnitude(events, show=True, savepath=None):
    """
    Create radar plots of phase and station counts binned by magnitude.

    For each magnitude range, the function displays the mean values of
    P phases, S phases, used phases, and station counts in a radar chart.
    Variability is represented using interquartile range (IQR) and the
    10–90 percentile envelope.

    Parameters
    ----------
    events : pandas.DataFrame
        DataFrame containing at least the following columns:
        'magnitude', 'p_phase_count', 's_phase_count',
        'used_phase_count', and 'station_count'.

    show : bool, optional
        Whether to display the figure on screen (default is True).

    savepath : str or None, optional
        If provided, the figure will be saved to this path with dpi=300.

    Returns
    -------
    None
    """

    # Columns to plot
    cols = ["p_phase_count", "s_phase_count", "used_phase_count", "station_count"]

    # Magnitude bins
    bins = [0, 1, 2, 3, 4, 5, 6, np.inf]
    labels = ["0-1", "1-2", "2-3", "3-4", "4-5", "5-6", ">6"]

    # Angles for radar
    angles = np.linspace(0, 2 * np.pi, len(cols), endpoint=False)

    def close(arr):
        """Close the radar plot loop."""
        return np.concatenate([arr, [arr[0]]])

    angles_closed = close(angles)

    # Create subplots (2 rows x 3 columns)
    fig, axes = plt.subplots(
        2, 3,
        figsize=(12, 8),
        subplot_kw={"polar": True}
    )
    axes = axes.flatten()

    dark_green = "#154734"   # UTD primary green
    light_green = "#69BE28"  # UTD secondary green

    valid_axes = 0

    for i in range(6):
        df_bin = events[
            (events["magnitude"] >= bins[i]) &
            (events["magnitude"] < bins[i + 1])
        ]

        if df_bin.empty:
            continue

        mean_vals = close(df_bin[cols].mean().values)
        q1_vals = close(df_bin[cols].quantile(0.25).values)
        q3_vals = close(df_bin[cols].quantile(0.75).values)
        p10_vals = close(df_bin[cols].quantile(0.10).values)
        p90_vals = close(df_bin[cols].quantile(0.90).values)

        ax = axes[i]

        # 10–90 percentile fill
        ax.fill_between(
            angles_closed,
            p10_vals,
            p90_vals,
            color=light_green,
            alpha=0.15,
            label="10–90%"
        )

        # IQR fill
        ax.fill_between(
            angles_closed,
            q1_vals,
            q3_vals,
            color=light_green,
            alpha=0.35,
            label="IQR (25–75%)"
        )

        # Mean line
        ax.plot(
            angles_closed,
            mean_vals,
            "o-",
            color=dark_green,
            linewidth=2,
            label="Mean"
        )

        # Pretty labels
        pretty_labels = ["P phase count", "S phase count", "Used phase count", "Station count"]

        # Hide default labels
        ax.set_xticks([])

        # Place manual labels
        for angle, label_text, idx in zip(angles, pretty_labels, range(len(pretty_labels))):
            y = ax.get_rmax() + 0.05 * ax.get_rmax()  # slightly outside
            rot = 90 if idx in [0, 2] else 0          # rotate P and Used phase count
            ax.text(
                angle,
                y,
                label_text,
                rotation=rot,
                rotation_mode="anchor",
                ha="center",
                va="center",
                fontsize=10,
                color="black"
            )

        # Title for each subplot
        ax.set_title(f"M {labels[i]}", loc="left", pad=15, 
                     color="orange", fontweight="bold",
                     fontsize=16)

        valid_axes = i

    # Remove empty subplots
    for j in range(valid_axes + 1, 6):
        fig.delaxes(axes[j])

    plt.tight_layout()

    # Add a single legend below all subplots
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="lower center",
        ncol=3,
        fontsize=16,
        frameon=False,
        bbox_to_anchor=(0.5, -0.07)
    )

    if savepath is not None:
        plt.savefig(savepath, dpi=300, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)

def plot_travel_time_vs_distance(
    picks,
    distance_unit="degrees",
    log_scale=False,
    show=True,
    savepath=None,
    point_size=5,
    chunk_size=50000
):
    """
    Plot travel time versus distance for seismic picks.

    Works with:
    - pandas DataFrame
    - streaming iterable datasets

    Parameters
    ----------
    picks : pandas.DataFrame or iterable
        Either a DataFrame with picks or a streaming iterator.

    distance_unit : str, optional
        "degrees" (default) or "km"

    log_scale : bool, optional
        Whether to use logarithmic scale on the x-axis.

    show : bool, optional
        Whether to display the plot.

    savepath : str or None, optional
        Path to save the figure.

    point_size : int, optional
        Size of scatter points.

    chunk_size : int, optional
        Number of records to accumulate before plotting
        when using streaming input.
    """

    fig, ax = plt.subplots(figsize=(10, 6))

    # Conversion factor
    km_per_degree = 111.19

    if distance_unit.lower() == "km":
        xlabel = "Distance (km)"
        convert = lambda d: d * km_per_degree
    else:
        xlabel = "Distance (degrees)"
        convert = lambda d: d

    # ----- CASE 1: Input is already a DataFrame -----
    if isinstance(picks, pd.DataFrame):

        required_cols = {"travel_time", "distance", "phase"}
        if not required_cols.issubset(picks.columns):
            raise ValueError(
                f"Input DataFrame must contain columns: {required_cols}"
            )

        df = picks.copy()
        df["distance_plot"] = convert(df["distance"])

        unique_phases = sorted(df["phase"].unique())
        n_phases = len(unique_phases)

        cmap = plt.get_cmap("tab20" if n_phases > 10 else "tab10")
        colors = cmap(np.linspace(0, 1, n_phases))

        color_map = {phase: colors[i] for i, phase in enumerate(unique_phases)}

        for phase in unique_phases:
            sub = df[df["phase"] == phase]

            ax.scatter(
                sub["distance_plot"],
                sub["travel_time"],
                s=point_size,
                alpha=1,
                color=color_map[phase],
                label=phase,
                marker='x'
            )

    # ----- CASE 2: Streaming iterable input -----
    else:

        chunk = []
        for i, pick in enumerate(picks):
            chunk.append(pick)

            if len(chunk) >= chunk_size:
                df = pd.DataFrame(chunk)
                df["distance_plot"] = convert(df["distance"])   # <-- add this!
                print(f"Processing chunk {i // chunk_size + 1}, size={len(df)}")  # log info

                for phase, sub in df.groupby("phase"):
                    ax.scatter(
                        sub["distance_plot"],
                        sub["travel_time"],
                        s=point_size,
                        alpha=1,
                        marker='x'
                    )

                chunk = []

        # Plot remaining data
        if chunk:
            df = pd.DataFrame(chunk)
            df["distance_plot"] = convert(df["distance"])  # <-- also here

            for phase, sub in df.groupby("phase"):
                ax.scatter(
                    sub["distance_plot"],
                    sub["travel_time"],
                    s=point_size,
                    alpha=1,
                    marker='x'
                )

    # ----- Common plot formatting -----

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Travel Time (s)")
    ax.set_title("Travel Time vs Distance by Phase Type")

    if log_scale:
        ax.set_xscale("log")

    ax.grid(True, alpha=0.3)
    ax.legend(title="Phase Type")

    plt.tight_layout()

    if savepath is not None:
        plt.savefig(savepath, dpi=300, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)

def tune_zoomed_travel_time_qc(axins: plt.Axes,
                               xlim: Tuple[float, float] = (0, 15),
                               ylim: Tuple[float, float] = (0, 50)) -> plt.Axes:
    """
    Configure a zoomed inset plot for travel-time QC.

    Ensures proper limits, custom tick labels, minor adjustments,
    and removes axis labels for the inset.

    Parameters
    ----------
    axins : plt.Axes
        Axes object for the inset plot.
    xlim : tuple, optional
        X-axis limits for the inset (default: (0, 15)).
    ylim : tuple, optional
        Y-axis limits for the inset (default: (0, 50)).

    Returns
    -------
    plt.Axes
        The configured inset axes.
    """
    ymax, xmax = ylim[1], xlim[1]

    # Formatter to hide labels at the edges
    def hide_edges_x(x, pos):
        return "" if np.isclose(x, 0) or np.isclose(x, xmax) else f"{x:g}"

    def hide_edges_y(y, pos):
        return "" if np.isclose(y, 0) or np.isclose(y, ymax) else f"{y:g}"

    x_multiplier = int(np.floor(xmax / 3))
    y_multiplier = int(np.floor(ymax / 3))

    axins.set_xlim(*xlim)
    axins.set_ylim(*ylim)
    axins.tick_params(labelsize=8)

    # Configure major ticks
    axins.xaxis.set_major_locator(MultipleLocator(x_multiplier))
    axins.xaxis.set_major_formatter(FuncFormatter(hide_edges_x))
    axins.yaxis.set_major_formatter(FuncFormatter(hide_edges_y))
    axins.tick_params(axis='y', direction='in', pad=-12)

    # Configure y-axis offset text
    axins.yaxis.get_offset_text().set_fontsize(8)
    axins.yaxis.get_offset_text().set_fontweight('bold')
    axins.yaxis.get_offset_text().set_fontfamily('serif')

    # Gridlines
    axins.grid(True, which="both", axis="y", linestyle="--", linewidth=0.5, alpha=0.3)

    # Remove labels and title for inset
    axins.set_xlabel("")
    axins.set_ylabel("")
    axins.set_title("")

    return axins


def plot_single_tt_qc(df: pd.DataFrame,
                      phase: str,
                      model: Optional[Any] = None,
                      zscore_threshold: float = 2,
                      show_text: bool = True,
                      show_models: Optional[List[str]] = None,
                      show_global_model: bool = True,
                      distance_col: str = "linear_hyp_distance",
                      tt_col: str = "travel_time",
                      x_limits: Optional[Tuple[float, float]] = None,
                      y_limits: Optional[Tuple[float, float]] = None,
                      ax: Optional[plt.Axes] = None) -> plt.Axes:
    """
    Plot travel-time QC for a single seismic phase.

    Highlights outliers based on z-score, optionally overlays model predictions
    and global trends.

    Parameters
    ----------
    df : pd.DataFrame
        Travel-time data containing distance, travel time, phase, and z-score.
    phase : str
        Seismic phase to plot (e.g., "P", "S").
    model : optional
        TravelTimeModel object containing model predictions.
    zscore_threshold : float, optional
        Z-score threshold to mark outliers (default: 2).
    show_text : bool, optional
        Display fraction of valid points inside z-score threshold (default: True).
    show_models : list of str, optional
        Columns in model to display (default: ["travel_time_p50"]).
    show_global_model : bool, optional
        Show global trend bounds (default: True).
    distance_col : str, optional
        Column name for distance (default: "linear_hyp_distance").
    tt_col : str, optional
        Column name for travel time (default: "travel_time").
    x_limits : tuple, optional
        X-axis limits (default: auto from data).
    y_limits : tuple, optional
        Y-axis limits (default: auto from data).
    ax : plt.Axes, optional
        Axes to plot on (default: creates new figure).

    Returns
    -------
    plt.Axes
        Axes object containing the plot.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))

    if show_models is None:
        show_models = ["travel_time_p50"]

    # Filter for phase and drop missing values
    df = df[df["phase"] == phase].dropna(subset=[distance_col, tt_col]).sort_values(distance_col)

    x, y = df[distance_col], df[tt_col]
    outside = np.abs(df["travel_time_zscore"]) > zscore_threshold
    inside = ~outside

    # Plot inliers and outliers
    ax.scatter(x[outside], y[outside], s=2, alpha=0.6, color="red",
               label=f"> {zscore_threshold} Zscore")
    ax.scatter(x[inside], y[inside], s=2, alpha=0.6, color="black",
               label=f"< {zscore_threshold} Zscore")

    # Display text annotation for fraction of points within z-score
    if show_text:
        n_total = len(x)
        n_inside = len(x) - len(x[outside])
        ax.text(
            0.95, 0.1, f"{human_format(n_inside)}/{human_format(n_total)}",
            transform=ax.transAxes,
            bbox=dict(facecolor="white", edgecolor="black",
                      boxstyle="round,pad=0.3", alpha=1),
            fontsize=12,
            ha="right",
            va="bottom"
        )

    # Plot global model bounds if available
    if show_global_model and phase in GLOBAL_TRENDS_DEFAULTS_DEG2:
        info = GLOBAL_TRENDS_DEFAULTS_DEG2[phase]
        poly = np.poly1d(info["coefficients"])
        sigma = info.get("sigma_median", 0)
        k = info.get("k", 5)

        y_pred = poly(np.asarray(x))
        lower_g = np.maximum(0, y_pred - k * sigma)
        upper_g = y_pred + k * sigma

        ax.plot(x, upper_g, color="blue", linestyle=":", linewidth=1, label="Global bounds")
        ax.plot(x, lower_g, color="blue", linestyle=":", linewidth=1)

    # Plot model curves if provided
    if model is not None:
        bins = np.unique(np.concatenate([model.model_df["distance_min"].values,
                                         model.model_df["distance_max"].values]))
        for col in show_models:
            model_df = model.model_df.sort_values("distance_center").dropna(subset=[col]).drop_duplicates("distance_center")
            dd, tt = model_df["distance_center"].values, model_df[col].values

            if len(dd) < 3:  # Not enough points for polynomial
                print(f"Skipping {col}: not enough points to fit polynomial")
                continue

            label = col.split("_")[-1].upper() if "_" in col else col
            linestyle = "-" if col == "travel_time_p50" else ".."
            color = "green" if col == "travel_time_p50" else None
            ax.plot(dd, tt, label=label, linestyle=linestyle, color=color, linewidth=1)

        # Add vertical lines for bin edges
        for c in bins:
            ax.axvline(c, color="black", linestyle="--", linewidth=0.5, alpha=0.2)

    # Grid and axis limits
    ax.grid(True, which="both", axis="y", linestyle="--", linewidth=0.5, alpha=0.3)
    if x_limits: ax.set_xlim(*x_limits)
    if y_limits: ax.set_ylim(*y_limits)

    return ax

def plot_travel_time_qc(df: pd.DataFrame,
               add_inset: bool = True,
               zscore_threshold: float = 2,
               show_text: bool = True,
               models: Optional[Dict[str, Any]] = None,
               show_models: Optional[List[str]] = None,
               show_global_model: bool = False,
               distance_col: str = "linear_hyp_distance",
               tt_col: str = "travel_time",
               x_inset_limits: Tuple[float, float] = (0, 30),
               y_inset_limits: Tuple[float, float] = (0, 10),
               savepath: Optional[str] = None
               ) -> Tuple[plt.Figure, np.ndarray, List[plt.Axes]]:
    """
    Plot multi-phase travel-time QC with optional inset zooms.

    Parameters
    ----------
    df : pd.DataFrame
        Travel-time data with multiple phases.
    add_inset : bool, optional
        Add zoomed inset plots (default: True).
    zscore_threshold : float, optional
        Z-score threshold for outlier detection (default: 2).
    show_text : bool, optional
        Show text annotations on each subplot (default: True).
    models : dict, optional
        Dictionary of TravelTimeModel objects keyed by phase.
    show_models : list of str, optional
        Columns in model to plot (default: ["travel_time_p50"]).
    show_global_model : bool, optional
        Display global trend bounds (default: False).
    distance_col : str, optional
        Column name for distance (default: "linear_hyp_distance").
    tt_col : str, optional
        Column name for travel time (default: "travel_time").
    x_inset_limits : tuple, optional
        X-axis limits for inset (default: (0, 30)).
    y_inset_limits : tuple, optional
        Y-axis limits for inset (default: (0, 10)).
    savepath : str, optional
        Path to save figure (default: None).

    Returns
    -------
    fig : plt.Figure
        The created figure.
    axes : np.ndarray
        Array of axes for each phase subplot.
    all_axins : list of plt.Axes
        List of inset axes.
    """
    phase_order = ("P", "Pn", "Pg", "S", "Sn", "Sg")
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    axes = axes.flatten()

    all_axins = []
    legend_handles, legend_labels = [], []

    for idx, phase in enumerate(phase_order):
        ax = axes[idx]
        phase_df = df[df["phase"] == phase].dropna(subset=[distance_col, tt_col])
        model_obj = models.get(phase) if models else None

        if phase_df.empty:
            ax.set_title(f"{phase} (no data)", fontweight="bold")
            ax.axis("off")
            continue

        ax.set_title(phase, fontweight="bold")
        ax = plot_single_tt_qc(
            phase_df, phase=phase,
            zscore_threshold=zscore_threshold,
            model=model_obj,
            show_text=show_text,
            show_models=show_models,
            show_global_model=show_global_model,
            ax=ax,
            distance_col=distance_col,
            tt_col=tt_col,
            x_limits=(0, phase_df[distance_col].max()),
            y_limits=(0, phase_df[tt_col].max())
        )

        # Conditional axis labels
        ax.set_ylabel("Travel time (s)" if idx in [0, 3] else "")
        ax.set_xlabel("Distance (km)" if idx in [3, 4, 5] else "")

        # Collect legend only once
        if not legend_handles:
            handles, labels = ax.get_legend_handles_labels()
            legend_handles.extend(handles)
            legend_labels.extend(labels)

        # Add inset if requested
        if add_inset:
            axins = inset_axes(ax, width="35%", height="35%", loc="upper left")
            axins = plot_single_tt_qc(
                phase_df, phase=phase,
                zscore_threshold=zscore_threshold,
                model=model_obj,
                show_text=False,
                show_models=show_models,
                show_global_model=show_global_model,
                ax=axins,
                distance_col=distance_col,
                tt_col=tt_col,
                x_limits=x_inset_limits,
                y_limits=y_inset_limits
            )
            tune_zoomed_travel_time_qc(axins, xlim=x_inset_limits, ylim=y_inset_limits)
            mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.5")
            all_axins.append(axins)

    fig.tight_layout()

    # Unified legend at bottom
    fig.legend(
        legend_handles, legend_labels,
        loc='lower center',
        bbox_to_anchor=(0.5, -0.05),
        ncol=len(legend_labels),
        markerscale=4,
        frameon=True,
        prop={'size': 12}
    )

    if savepath:
        fig.savefig(savepath, dpi=300, bbox_inches='tight')
        print(f"Saved figure to {savepath}")

    return fig, axes, all_axins