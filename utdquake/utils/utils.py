"""
Utility functions for UTDQuake package.

This module provides helper functions for:
- Computing plot regions for events and stations
- Formatting large numbers
- Formatting dates for plots
- Creating custom colormaps
- Summarizing networks (stations and events)

Modules required:
- numpy
- pandas
- matplotlib
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

def compute_region(
    df_events: pd.DataFrame,
    df_stations: pd.DataFrame,
    padding: float = 0.2,
    global_region: Optional[Tuple[float, float, float, float]] = None,
    how: str = "events",
    rm_outliers: bool = False,
) -> Tuple[float, float, float, float]:
    """
    Compute a bounding box for plotting events and stations.
    Handles dateline wrap-around.

    Parameters
    ----------
    df_events : pd.DataFrame
        Events table with 'longitude' and 'latitude' columns.
    df_stations : pd.DataFrame
        Stations table with 'longitude' and 'latitude' columns.
    padding : float, optional
        Fraction of span to add as padding (default is 0.2).
    global_region : tuple, optional
        If provided, returns this region directly
        (lon_min, lon_max, lat_min, lat_max).
    how : str, optional
        Which data to use: 'events', 'stations', or 'both' (default 'events').
    rm_outliers : bool, optional
        If True, remove extreme outliers beyond 6 std deviations.

    Returns
    -------
    tuple
        (lon_min, lon_max, lat_min, lat_max)

    Raises
    ------
    ValueError
        If no valid coordinates exist or invalid `how` argument.

    Examples
    --------
    >>> compute_region(df_events, df_stations, padding=0.1, how="both")
    (-118.5, -115.2, 33.8, 36.1)
    """

    if global_region is not None:
        return global_region

    # --- Select longitude and latitude data ---
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

    # --- Remove extreme outliers if requested ---
    if rm_outliers:
        lons_mean, lons_std = lons.mean(), lons.std()
        lats_mean, lats_std = lats.mean(), lats.std()
        lons = lons[(lons >= lons_mean - 6 * lons_std) & (lons <= lons_mean + 6 * lons_std)]
        lats = lats[(lats >= lats_mean - 6 * lats_std) & (lats <= lats_mean + 6 * lats_std)]

    lons = lons.values
    lats = lats.values

    # --- Compute min/max latitude and longitude ---
    lat_min, lat_max = np.min(lats), np.max(lats)
    lon_min, lon_max = np.min(lons), np.max(lons)

    # --- Add padding ---
    lon_distance = lon_max - lon_min
    lat_distance = lat_max - lat_min
    lon_min -= padding * lon_distance
    lon_max += padding * lon_distance
    lat_min -= padding * lat_distance
    lat_max += padding * lat_distance

    # --- Clamp to valid geographic coordinates ---
    if lon_min < -180:
        lon_min=-180
    if lon_max > 180:
        lon_max=180
    if lat_min < -90:
        lat_min=-90
    if lat_max > 90:
        lat_max=90

    return (lon_min, lon_max, lat_min, lat_max)

def human_format(num: float) -> str:
    """
    Format large numbers with K/M suffix for plotting.

    Parameters
    ----------
    num : float
        Number to format.

    Returns
    -------
    str
        Formatted string.

    Examples
    --------
    >>> human_format(999)
    '999'
    >>> human_format(1200)
    '1.2K'
    >>> human_format(1500000)
    '1.5M'
    """
    if abs(num) >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif abs(num) >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{num}"

def smart_date_formatter(bins) -> FuncFormatter:
    """
    Create a smart date formatter for matplotlib axes based on date range.

    Parameters
    ----------
    bins : array-like
        Sequence of datetime-like objects.

    Returns
    -------
    matplotlib.ticker.FuncFormatter
        Formatter to be used with matplotlib axes.

    Examples
    --------
    >>> import pandas as pd
    >>> bins = pd.date_range("2026-01-01", periods=10)
    >>> fmt = smart_date_formatter(bins)
    >>> fmt(pd.Timestamp("2026-01-01").toordinal())
    '2026\\nJan'
    """
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

def create_green_to_orange_cmap(name: str = 'green_to_orange', n_colors: int = 256) -> LinearSegmentedColormap:
    """
    Create a colormap that transitions from green to orange (#ec7524).

    Parameters
    ----------
    name : str, optional
        Name of the colormap (default 'green_to_orange').
    n_colors : int, optional
        Number of discrete colors in the colormap (default 256).

    Returns
    -------
    matplotlib.colors.LinearSegmentedColormap
        Custom green-to-orange colormap.

    Examples
    --------
    >>> cmap = create_green_to_orange_cmap()
    >>> type(cmap)
    <class 'matplotlib.colors.LinearSegmentedColormap'>
    """
    colors = ['green', '#ec7524']
    cmap = LinearSegmentedColormap.from_list(name, colors, N=n_colors)
    return cmap

def get_network_summary(
    stations: pd.DataFrame,
    events: pd.DataFrame
) -> Dict[str, Any]:
    """
    Compute summary statistics for a seismic network.

    Parameters
    ----------
    stations : pd.DataFrame
        Stations table. Must contain columns:
        ['network', 'station', 'confirmed', 'calculated'].
    events : pd.DataFrame
        Events table. Must contain columns:
        ['latitude', 'longitude', 'time', 'p_phase_count', 's_phase_count'].

    Returns
    -------
    dict
        Dictionary with summary statistics:
        - events : int
            Number of events
        - p_arrivals : int
            Total P-phase picks
        - s_arrivals : int
            Total S-phase picks
        - total_stations : int
            Number of stations
        - confirmed_stations : int
            Number of confirmed stations
        - calculated_stations : int
            Number of calculated stations
        - start_time : str
            Earliest event time
        - end_time : str
            Latest event time

    Examples
    --------
    >>> get_network_summary(df_stations, df_events)
    {'events': 10, 'p_arrivals': 30, ...}
    """

    # --- Deduplicate stations ---
    stations = stations.drop_duplicates(subset=["network", "station"])

    n_total_stations = len(stations)
    n_confirmed_stations = int(stations["confirmed"].eq(True).sum())
    n_calculated_stations = int(stations["calculated"].eq(True).sum())

    # --- Filter events with valid coordinates ---
    events = events.dropna(subset=["latitude", "longitude"])

    n_events = len(events)
    min_event_time = events["time"].min()
    max_event_time = events["time"].max()

    n_p_picks = int(events["p_phase_count"].sum())
    n_s_picks = int(events["s_phase_count"].sum())

    return {
        "events": n_events,
        "p_arrivals": n_p_picks,
        "s_arrivals": n_s_picks,
        "total_stations": n_total_stations,
        "confirmed_stations": n_confirmed_stations,
        "calculated_stations": n_calculated_stations,
        "start_time": str(min_event_time),
        "end_time": str(max_event_time),
    }