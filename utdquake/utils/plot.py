"""
plot.py  
(This can be improved significantly with more modularization later... I am a bit lazy to do it now)

Functions for plotting seismic data, including:

- Network and event overview maps (plot_overview, plot_utdq_overview)
- Seismic statistics and histograms (plot_stats, plot_pick_histograms)
- Uncertainty visualization (plot_uncertainty_boxplots)
- Utility functions like add_scalebar

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
from typing import Dict, Any, Tuple, Optional

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

# Seaborn
import seaborn as sns

# SciPy
from scipy.stats import linregress

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
    region: Optional[Tuple[float, float, float, float]] = None,
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
    region : tuple, optional
        Map extent (lon_min, lon_max, lat_min, lat_max). Default: None.
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


    ax1.set_title(f"Contributor: {analysis.get('network', 'N/A')}",
                  fontsize=14, weight='bold',loc='left')
    ax1.text(
        0.70, 0.8,
        f"Events: {human_format(analysis.get('events', len(events)))}\n"
        f"Total Stations: {human_format(analysis.get('total_stations', 'N/A'))}\n"
        f"   Calculated: {human_format(analysis.get('calculated_stations', 'N/A'))}\n"
        f"   Confirmed: {human_format(analysis.get('confirmed_stations', 'N/A'))}\n"
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

    ax2.scatter(
        stations['calculated_longitude'],
        stations['calculated_latitude'],
        marker="^",
        c="green",
        s=40,
        alpha=0.7,
        transform=ccrs.PlateCarree(),
        label="Stations"
    )
    ax2.legend(loc="lower right", fontsize=12)

    ax2.text(
        0.02, 0.05,
        f"Total Stations: {human_format(analysis.get('total_stations', 'N/A'))}\n"
        f"   Calculated: {human_format(analysis.get('calculated_stations', 'N/A'))}\n"
        f"   Confirmed: {human_format(analysis.get('confirmed_stations', 'N/A'))}",
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

def plot_pick_stats(df, savepath=None, show=True):

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
    savepath : str or pathlib.Path, optional
        If provided, the final combined figure is saved to this path.

    Returns
    -------
    matplotlib.figure.Figure
        The combined multi-panel figure containing all jointplots.
    """
    
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

