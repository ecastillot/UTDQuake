import numpy as np
import pandas as pd
from typing import Dict, Any
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter, MultipleLocator, ScalarFormatter

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

def smart_date_formatter(bins):
    

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

def get_network_summary(
    stations: pd.DataFrame,
    events: pd.DataFrame
) -> Dict[str, Any]:
    """
    Compute summary statistics for stations and events.

    Parameters
    ----------
    stations : pd.DataFrame
        Stations table. Must contain columns:
        ['network', 'station', 'confirmed', 'calculated'].
    events : pd.DataFrame
        Events table. Must contain columns:
        ['latitude', 'longitude', 'time',
         'p_phase_count', 's_phase_count'].

    Returns
    -------
    dict
        Dictionary with summary statistics.
    """

    # --- Stations ---
    stations = stations.drop_duplicates(subset=["network", "station"])

    n_total_stations = len(stations)
    n_confirmed_stations = int(stations["confirmed"].eq(True).sum())
    n_calculated_stations = int(stations["calculated"].eq(True).sum())

    # --- Events ---
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