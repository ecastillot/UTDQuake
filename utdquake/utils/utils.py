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
    coverage: Optional[float] = None,
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
    coverage : float, optional
        Keep the central ``coverage`` fraction of the points in longitude and
        in latitude (e.g. 0.95: 2.5th to 97.5th percentiles), so that a few
        distant points do not stretch the region while many of them do.

    Returns
    -------
    tuple
        (lon_min, lon_max, lat_min, lat_max). For data across the
        antimeridian (e.g. the Aleutians: 179 E and 170 W) the longitudes are
        given in [0, 360) (e.g. 160 to 215) when that is the tighter and
        under-180-degree range; plot it with :func:`map_projection`.

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

    # --- Data across the antimeridian: work in [0, 360) when that range is
    # tighter and under 180 degrees (e.g. the Aleutians) ---
    lons360 = lons % 360
    if np.ptp(lons360) < np.ptp(lons) and np.ptp(lons360) < 180:
        lons = lons360

    # --- Keep the central part of the points if requested ---
    if coverage is not None:
        q = (1 - coverage) / 2
        lons = lons[(lons >= lons.quantile(q)) & (lons <= lons.quantile(1 - q))]
        lats = lats[(lats >= lats.quantile(q)) & (lats <= lats.quantile(1 - q))]

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

    # print(f"Initial region: lon_min={lon_min}, lon_max={lon_max}, lat_min={lat_min}, lat_max={lat_max}")

    # --- Add padding ---
    lon_distance = lon_max - lon_min
    lat_distance = lat_max - lat_min
    lon_min -= padding * lon_distance
    lon_max += padding * lon_distance
    lat_min -= padding * lat_distance
    lat_max += padding * lat_distance
    # print(f"region after: lon_min={lon_min}, lon_max={lon_max}, lat_min={lat_min}, lat_max={lat_max}")

    # --- Clamp to valid geographic coordinates ---
    if lon_max - lon_min > 360:
        lon_min, lon_max = -180, 180
    if lon_min < -180:
        lon_min=-180
    if lon_max > 180 and lon_min < 0:
        lon_max=180
    if lat_min < -90:
        lat_min=-90
    if lat_max > 90:
        lat_max=90

    return (lon_min, lon_max, lat_min, lat_max)

def map_projection(region):
    """
    PlateCarree projection for a ``(lon_min, lon_max, lat_min, lat_max)``
    region: centered on 180 deg when the region crosses the antimeridian
    (``lon_max > 180``, see :func:`compute_region`), else the default.
    """
    import cartopy.crs as ccrs
    if region is not None and region[1] > 180:
        return ccrs.PlateCarree(central_longitude=180)
    return ccrs.PlateCarree()


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
        return f"{num/1_000_000:.1f} M"
    elif abs(num) >= 1_000:
        return f"{num/1_000:.1f} K"
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

def phase_family(phase: pd.Series) -> pd.Series:
    """
    Return the phase family of each pick label: "P" for P-type labels
    (P, Pg, Pn, Pb, ...), "S" for S-type labels (S, Sg, Sn, ...), else <NA>.
    The labels themselves are kept in the picks table; the family is only
    used to count and group picks.

    Examples
    --------
    >>> phase_family(pd.Series(["P", "Pg", "Sn", "S", "X"])).tolist()
    ['P', 'P', 'S', 'S', <NA>]
    """
    first = phase.astype("string").str[0]
    return first.where(first.isin(["P", "S"]))


def phase_counts(picks: pd.DataFrame, by: Optional[str] = None) -> pd.DataFrame:
    """
    Count picks by phase label and by phase family.

    Parameters
    ----------
    picks : pd.DataFrame
        Picks table (column ``phase``, and ``by`` if given).
    by : str, optional
        Column to group by, e.g. ``"event_id"``. Default: one row for all picks.

    Returns
    -------
    pd.DataFrame
        Columns ``{label.lower()}_count`` for each label of
        :data:`utdquake.writers.schema.PHASE_LABELS` (P, Pg, Pn, S, Sg, Sn),
        ``p_arrivals`` (all P-type picks) and ``s_arrivals`` (all S-type
        picks), indexed by ``by``.

    Examples
    --------
    >>> phase_counts(pd.DataFrame({"phase": ["P", "Pg", "Sn"]}))[["p_count", "p_arrivals", "s_arrivals"]]
       p_count  p_arrivals  s_arrivals
    0        1           2           1
    """
    from ..writers.schema import PHASE_LABELS, PHASE_COUNT_COLS

    phase = picks["phase"].astype("string")
    df = pd.DataFrame({f"{label.lower()}_count": phase.eq(label).fillna(False).astype("int64")
                       for label in PHASE_LABELS}, index=picks.index)
    family = phase_family(phase)
    df["p_arrivals"] = family.eq("P").fillna(False).astype("int64")
    df["s_arrivals"] = family.eq("S").fillna(False).astype("int64")
    if by is None:
        return df.sum().to_frame().T[PHASE_COUNT_COLS]
    return df.groupby(picks[by]).sum()[PHASE_COUNT_COLS]


def add_phase_counts(events: pd.DataFrame, picks: pd.DataFrame) -> pd.DataFrame:
    """Return ``events`` with the per-event :func:`phase_counts` of ``picks`` (0 for events without picks)."""
    from ..writers.schema import PHASE_COUNT_COLS

    counts = phase_counts(picks, by="event_id")
    events = events.drop(columns=PHASE_COUNT_COLS, errors="ignore")
    events = events.merge(counts, left_on="event_id", right_index=True, how="left")
    events[PHASE_COUNT_COLS] = events[PHASE_COUNT_COLS].fillna(0).astype("int64")
    return events


def get_network_summary(
    stations: pd.DataFrame,
    events: pd.DataFrame,
    das: bool = False,
    picks: Optional[pd.DataFrame] = None,
    distinct_stations: bool = False,
) -> Dict[str, Any]:
    """
    Compute summary statistics for one or more UTDQuake networks.

    Parameters
    ----------
    stations : pd.DataFrame
        Stations table. Must contain columns:
        ['network', 'station', 'confirmed', 'calculated'] (``network`` is the
        FDSN code; with ``utdq_net`` too, a station seen by two UTDQuake
        networks counts once for each).
    events : pd.DataFrame
        Events table. Must contain columns:
        ['latitude', 'longitude', 'time', 'p_phase_count', 's_phase_count'].
    das : bool, optional
        Whether to use DAS dataset. Default is False.
    picks : pd.DataFrame, optional
        Picks table (column ``phase``). When given, ``p_arrivals`` and
        ``s_arrivals`` count its P-type and S-type picks (see
        :func:`phase_family`). Without it they are the sums of the events'
        ``p_arrivals``/``s_arrivals`` columns, or, for an events table without
        them, of ``p_phase_count``/``s_phase_count``, which only count
        arrivals labelled exactly "P" or "S" (Pg, Pn, Sg, Sn are left out).
    distinct_stations : bool, optional
        Count physical stations, i.e. distinct ``(network, station)`` pairs
        across UTDQuake networks: a station used by several networks counts
        once, as confirmed (calculated) if any of its rows is. Default False:
        with ``utdq_net``, a station counts once per UTDQuake network (the
        counts of the network table). Use True for totals over several
        networks.

    Returns
    -------
    dict
        Dictionary with summary statistics:
        - events : int
            Number of events
        - p_arrivals : int
            Total P-type picks (P, Pg, Pn, ...)
        - s_arrivals : int
            Total S-type picks (S, Sg, Sn, ...)
        - p_count, pg_count, pn_count, s_count, sg_count, sn_count : int
            Picks of each phase label (only when ``picks`` is given)
        - total_stations : int
            Number of stations
        - located_stations : int
            Number of stations that have their location either confirmed or calculated
        - confirmed_stations : int
            Number of confirmed stations
        - calculated_stations : int
            Number of calculated stations
        - only_calculated_stations : int
            Number of stations that are calculated but not confirmed
        - start_time : str
            Earliest event time
        - end_time : str
            Latest event time
        - approx_lat_min : float or None
            Approximate southern edge of station coverage (confirmed
            location, falling back to calculated location).
        - approx_lat_max : float or None
            Approximate northern edge of station coverage.
        - approx_lon_min : float or None
            Approximate western edge of station coverage.
        - approx_lon_max : float or None
            Approximate eastern edge of station coverage.

    Examples
    --------
    >>> get_network_summary(df_stations, df_events)
    {'events': 10, 'p_arrivals': 30, ...}
    """
    # --- Deduplicate stations ---
    key = ["utdq_net"] if "utdq_net" in stations.columns and not distinct_stations else []
    if distinct_stations:
        sta_keys = ["network", "station"] + (["channel"] if das else [])
        flags = (stations[sta_keys]
                 .assign(confirmed=stations["confirmed"].fillna(False).astype(bool),
                         calculated=stations["calculated"].fillna(False).astype(bool))
                 .groupby(sta_keys)[["confirmed", "calculated"]].transform("any"))
        stations = stations.assign(confirmed=flags["confirmed"], calculated=flags["calculated"])
    if das:
        stations = stations.drop_duplicates(subset=key + ["network", "station", "channel"])
        n_total_stations = len(stations.drop_duplicates(subset=key + ["network", "station"]))
    else:
        stations = stations.drop_duplicates(subset=key + ["network", "station"])
        n_total_stations = len(stations)

    n_confirmed_stations = int(stations["confirmed"].eq(True).sum())
    # Only count as calculated if it's not also confirmed. 
    # This avoids double-counting stations that are both confirmed and calculated.
    n_only_calculated_stations = int(
                                (
                                    stations["calculated"].fillna(False) &
                                    ~stations["confirmed"].fillna(False)
                                ).sum()
                            ) 

    # Alternatively, if we want to count all calculated stations regardless of confirmed status, we could use:
    n_calculated_stations = int(stations["calculated"].eq(True).sum())

    # --- Approximate station bounding box (confirmed location, falling
    # back to calculated location when a station has no confirmed one) ---
    sta_lat = stations["confirmed_latitude"]
    sta_lon = stations["confirmed_longitude"]
    if "calculated_latitude" in stations.columns:
        sta_lat = sta_lat.fillna(stations["calculated_latitude"])
        sta_lon = sta_lon.fillna(stations["calculated_longitude"])

    approx_lat_min = float(sta_lat.min()) if sta_lat.notna().any() else None
    approx_lat_max = float(sta_lat.max()) if sta_lat.notna().any() else None
    approx_lon_min = float(sta_lon.min()) if sta_lon.notna().any() else None
    approx_lon_max = float(sta_lon.max()) if sta_lon.notna().any() else None

    # --- Filter events with valid coordinates ---
    events = events.dropna(subset=["latitude", "longitude"])

    n_events = len(events)
    min_event_time = events["time"].min()
    max_event_time = events["time"].max()

    counts = {}
    if picks is not None:
        counts = {k: int(v) for k, v in phase_counts(picks).iloc[0].items()}
        n_p_picks = counts.pop("p_arrivals")
        n_s_picks = counts.pop("s_arrivals")
    elif {"p_arrivals", "s_arrivals"} <= set(events.columns):
        # per-event phase-family counts of the events table (see add_phase_counts)
        n_p_picks = int(events["p_arrivals"].sum())
        n_s_picks = int(events["s_arrivals"].sum())
    else:
        n_p_picks = int(events["p_phase_count"].sum())
        n_s_picks = int(events["s_phase_count"].sum())

    data =  {
        "events": n_events,
        "p_arrivals": n_p_picks,
        "s_arrivals": n_s_picks,
        **counts,
        "total_stations": n_total_stations,
        "located_stations": n_confirmed_stations + n_only_calculated_stations,
        "confirmed_stations": n_confirmed_stations,
        "calculated_stations": n_calculated_stations,
        # "unlocated_stations": n_total_stations - (n_confirmed_stations + n_only_calculated_stations),
        # "only_calculated_stations": n_only_calculated_stations,
        "start_time": str(min_event_time),
        "end_time": str(max_event_time),
        "approx_lat_min": approx_lat_min,
        "approx_lat_max": approx_lat_max,
        "approx_lon_min": approx_lon_min,
        "approx_lon_max": approx_lon_max,
    }

    if das:
        data["total_channels"] = len(stations["channel"])

    return data