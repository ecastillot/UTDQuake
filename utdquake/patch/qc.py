import numpy as np
from obspy import Catalog

#: Default QC parameters for pick-level filtering in UTDQuake.
#: Passed to :func:`picks_qc` if `pick_qc_args=None` in
#: :func:`apply_utdquake_qc_to_catalog`.
#:
#: Keys
#: ----
#: - min_travel_time : float
#:     Minimum allowed travel time (seconds).
#: - min_linear_hyp_distance : float
#:     Minimum hypocentral distance (km).
#: - min_epicentral_distance : float
#:     Minimum epicentral distance (degrees).
#: - sp_threshold : dict of tuple -> tuple
#:     Phase pairs mapped to allowed S–P time difference ranges.
#:     Example: {("S", "P"): (0, np.inf)}
#: - debug : bool
#:     If True, prints debug information.
#: - apply_to_nans : bool
#:     If True, rows with NaNs in the QC columns are removed.
PICK_QC_DEFAULTS = {
    "min_travel_time": 0,
    "min_linear_hyp_distance": 0,
    "min_epicentral_distance": 0,
    "sp_threshold": {
        ("S", "P"): (0, np.inf),
        ("Sn", "Pn"): (0, np.inf),
        ("Sg", "Pg"): (0, np.inf),
    },
    "debug": False,
    "apply_to_nans": False,
}


#: Default QC parameters for event-level filtering in UTDQuake.
#: Passed to :func:`events_qc` if `event_qc_args=None` in
#: :func:`apply_utdquake_qc_to_catalog`.
#:
#: Keys
#: ----
#: - min_associated_phase_count : int
#:     Minimum number of associated phases per event.
#: - min_used_phase_count : int
#:     Minimum number of used phases per event.
#: - min_station_count : int
#:     Minimum number of stations per event.
#: - max_standard_error : float
#:     Maximum allowed event location standard error.
#: - debug : bool
#:     If True, prints debug information.
#: - apply_to_nans : bool
#:     If True, rows with NaNs in QC columns are removed.
EVENT_QC_DEFAULTS = {
    "min_associated_phase_count": 4,
    "min_used_phase_count": 4,
    "min_station_count": 3,
    "max_standard_error": 1.8,
    "debug": False,
    "apply_to_nans": False,
}


def apply_utdq_qc(cat, debug=True, inplace=False):
    """
    Apply UTDQuake pick-level and event-level QC to a catalog.

    Wrapper around :func:`apply_utdquake_qc_to_catalog` for convenience.

    Parameters
    ----------
    cat : obspy.core.event.Catalog
        ObsPy Catalog to filter.
    debug : bool, default True
        Enable verbose output during all QC steps.
    inplace : bool, default False
        If True, modify the catalog in place. Otherwise, return a
        new filtered catalog.

    Returns
    -------
    obspy.core.event.Catalog or None
        - If `inplace=False`, returns a new filtered catalog.
        - If `inplace=True`, updates the catalog in place and returns None.

    See Also
    --------
    :func:`~utdquake.core.qc.apply_utdquake_qc_to_catalog` : Full QC workflow function.
    :data:`~utdquake.core.qc.PICK_QC_DEFAULTS` : Default pick QC parameters.
    :data:`~utdquake.core.qc.EVENT_QC_DEFAULTS` : Default event QC parameters.
    """
    filtered_cat = apply_utdquake_qc_to_catalog(cat, debug=debug)

    if inplace:
        # Replace events, origins, arrivals, and picks
        cat.events = filtered_cat.events
        return None
    else:
        return filtered_cat


def apply_utdquake_qc_to_catalog(cat,pick_qc_args=None,
                                 event_qc_args=None, 
                                 debug=False):
    """
    Apply UTDQuake pick-level and event-level QC sequentially
    to an ObsPy Catalog.

    The workflow is:

    1. Convert picks to DataFrame
    2. Apply pick-level QC via :func:`picks_qc`
    3. Filter catalog picks and arrivals using :func:`apply_picks_qc_to_catalog`
    4. Convert events to DataFrame
    5. Apply event-level QC via :func:`events_qc`
    6. Filter catalog events using :func:`apply_events_qc_to_catalog`

    Parameters
    ----------
    cat : obspy.core.event.Catalog
        Input ObsPy Catalog containing events, origins, arrivals,
        and picks.

    pick_qc_args : dict, optional
        Dictionary of keyword arguments passed to :func:`picks_qc`.

        If None, UTDQuake defaults defined in :data:`PICK_QC_DEFAULTS` are used.

        Users may provide a partial dictionary to override specific parameters.

        See Also
        --------
        picks_qc : Full list of available pick QC parameters.

    event_qc_args : dict, optional
        Dictionary of keyword arguments passed to :func:`events_qc`.

        If None, UTDQuake defaults defined in :data:`EVENT_QC_DEFAULTS` are used.

        Users may provide a partial dictionary to override specific parameters.

        See Also
        --------
        events_qc : Full list of available event QC parameters.

    debug : bool, default False
        If True, enables verbose output during all QC stages.
        This flag is also propagated to the underlying QC functions
        unless explicitly overridden in the argument dictionaries.

    Returns
    -------
    obspy.core.event.Catalog
        Catalog filtered according to both pick-level and
        event-level QC criteria.

    Notes
    -----
    - **Pick-level QC is always applied first.** Events are not filtered
      until picks have been QCed, so event-level QC operates on a catalog
      already filtered at the pick level.
    - Default QC parameter constants (:data:`PICK_QC_DEFAULTS` and
      :data:`EVENT_QC_DEFAULTS`) can be inspected or modified by advanced users.
    - Users can override any parameter in the defaults by providing a
      dictionary to ``pick_qc_args`` or ``event_qc_args``.
    
    """
    # ---------------------------------------------------------------------
    # Default pick QC parameters
    # ---------------------------------------------------------------------
    # Pick-level QC
    pick_args = PICK_QC_DEFAULTS.copy()
    if pick_qc_args:
        pick_args.update(pick_qc_args)
    pick_args["debug"] = debug

    # ---------------------------------------------------------------------
    # Default event QC parameters
    # ---------------------------------------------------------------------
    # Event-level QC
    event_args = EVENT_QC_DEFAULTS.copy()
    if event_qc_args:
        event_args.update(event_qc_args)
    event_args["debug"] = debug
    
    # ---------------------------------------------------------------------
    # Pick-level QC
    # ---------------------------------------------------------------------
    picks = cat.utdq_picks_to_df()

    if debug:
        ini_picks_len = len(picks)
        print("\n#### Starting pick-level QC ####")
        print(f"Initial catalog: {ini_picks_len} picks")
        print("Parameters:", pick_args, "\n")

    picks = picks_qc(picks, **pick_args)
    cat = apply_picks_qc_to_catalog(cat, picks, debug=debug)
    
    if debug:
        print("#### Pick-level QC complete ####")

    # ---------------------------------------------------------------------
    # Event-level QC
    # ---------------------------------------------------------------------
    events = cat.utdq_events_to_df()
    if debug:
        ini_events_len = len(events)
        print("\n#### Starting event-level QC ####")
        print(f"Initial catalog: {ini_events_len } events")
        print("Parameters:", event_args, "\n")

    events = events_qc(events, **event_args)
    cat = apply_events_qc_to_catalog(cat, events, debug=debug)

    if debug:
        print("#### Event-level QC complete ####")

    return cat


def apply_picks_qc_to_catalog(cat: Catalog, df_qc, debug=False) -> Catalog:
    """
    Apply QC from a picks DataFrame to an ObsPy Catalog.

    Keeps only Arrivals and Picks corresponding to the QCed picks.

    Parameters
    ----------
    cat : obspy.Catalog
        Input ObsPy Catalog with events, origins, arrivals, and picks.
    df_qc : pandas.DataFrame
        QCed picks DataFrame (output of `qc_picks`).
        Must contain columns 'pick_id' and 'resource_id'.
    debug : bool, default False
        If True, prints summary of removals per event and final QC totals.

    Returns
    -------
    obspy.Catalog
        Catalog with arrivals and picks filtered by QC.
    """

    # --- Sets of IDs to keep ---
    pick_ids_to_keep = set(df_qc["pick_id"].astype(str).values)
    arrival_ids_to_keep = set(df_qc["resource_id"].astype(str).values)

    total_arrivals = sum(len(event.preferred_origin().arrivals) 
                         for event in cat if event.preferred_origin())
    total_picks = sum(len(event.picks) if hasattr(event, "picks") else 0 for event in cat)

    removed_arrivals_cum = 0
    removed_picks_cum = 0

    if debug:
        print(f"QC start: {total_arrivals} arrivals, {total_picks} picks in catalog.")

    # --- Loop over events ---
    for event in cat:
        origin = event.preferred_origin()
        if not origin:
            continue

        # Filter arrivals
        kept_arrivals = [arr for arr in origin.arrivals if str(arr.resource_id) in arrival_ids_to_keep]
        removed_arrivals = len(origin.arrivals) - len(kept_arrivals)
        origin.arrivals = kept_arrivals
        removed_arrivals_cum += removed_arrivals

        if debug and removed_arrivals > 0:
            print(f"Event {event.resource_id}: removed {removed_arrivals} arrivals.")

        # Filter picks
        if hasattr(event, "picks") and event.picks:
            kept_picks = [p for p in event.picks if str(p.resource_id) in pick_ids_to_keep]
            removed_picks = len(event.picks) - len(kept_picks)
            event.picks = kept_picks
            removed_picks_cum += removed_picks

            if debug and removed_picks > 0:
                print(f"Event {event.resource_id}: removed {removed_picks} picks.")

    # --- Final QC summary ---
    if debug:
        print(
            f"Final Summary:"
            f"QC completed: removed {removed_arrivals_cum}/{total_arrivals} arrivals, "
            f"{removed_picks_cum}/{total_picks} picks. "
            f"Remaining: {total_arrivals - removed_arrivals_cum} arrivals, "
            f"{total_picks - removed_picks_cum} picks."
        )

    return cat


def apply_events_qc_to_catalog(cat: Catalog, df_qc, debug=False) -> Catalog:
    """
    Apply QC from an events DataFrame to an ObsPy Catalog.

    Keeps only events whose event_id exists in the QCed DataFrame.

    Parameters
    ----------
    cat : obspy.Catalog
        Input ObsPy Catalog.
    df_qc : pandas.DataFrame
        QCed events DataFrame (output of `events_qc`).
        Must contain column 'event_id'.
    debug : bool, default False
        If True, prints summary of removals.

    Returns
    -------
    obspy.Catalog
        Catalog filtered by event-level QC.
    """

    # --- IDs to keep ---
    event_ids_to_keep = set(df_qc["event_id"].astype(str).values)

    total_events = len(cat)
    removed_events = 0

    if debug:
        print(f"QC start: {total_events} events in catalog.")

    filtered_events = []

    for event in cat:
        event_id = str(event.resource_id)

        if event_id in event_ids_to_keep:
            filtered_events.append(event)
        else:
            removed_events += 1
            if debug:
                print(f"\tRemoved event {event_id}")

    new_catalog = Catalog(events=filtered_events)

    if debug:
        print(
            f"Final Summary:"
            f"QC completed: removed {removed_events}/{total_events} events "
            f"({(removed_events / total_events * 100):.2f}%). "
            f"Remaining: {len(new_catalog)} events."
        )

    return new_catalog


def picks_qc(
    df,
    min_travel_time=0,
    max_travel_time=np.inf,
    min_linear_hyp_distance=0,
    max_linear_hyp_distance=np.inf,
    min_epicentral_distance=0,
    max_epicentral_distance=np.inf,
    sp_threshold={
        ("S", "P"): (0, np.inf),
        ("Sn", "Pn"): (0, np.inf),
        ("Sg", "Pg"): (0, np.inf),
    },
    debug=False,
    apply_to_nans=False,
):
    """
    Apply quality-control filters to seismic picks.

    Filters applied
    ---------------
    1. Travel time limits (seconds)
    2. Hypocentral distance limits (km)
    3. Epicentral distance limits (degrees)
    4. S–P consistency threshold per event and station

    Required Columns in `df`
    ------------------------
    - 'travel_time' : float (seconds)
    - 'linear_hyp_distance' : float (km)
    - 'distance' : float (degrees)
    - 'phase' : str
    - 'event_id' : str or int
    - 'station' : str

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing pick information.
    min_travel_time, max_travel_time : float
        Allowed travel time range (seconds).
    min_linear_hyp_distance, max_linear_hyp_distance : float
        Allowed hypocentral distance range (km).
    min_epicentral_distance, max_epicentral_distance : float
        Allowed epicentral distance range (degrees).
    sp_threshold : dict
        Dictionary mapping phase pairs to allowed S–P
        time difference ranges in seconds.
        Example: {("S", "P"): (10, np.inf)}
    debug : bool, default False
        If True, prints information about why picks are removed.
    apply_to_nans : bool, default False
        If True, rows with NaN in travel_time, linear_hyp_distance,
        or distance will be removed. If False, NaNs are ignored.

    Returns
    -------
    pandas.DataFrame
        Filtered DataFrame after QC.
    """

    original_total = len(df)
    cumulative_removed = 0
    df_filtered = df.copy()

    # --- Travel time filter ---
    mask = df_filtered["travel_time"].between(min_travel_time, max_travel_time)
    if not apply_to_nans:
        mask |= df_filtered["travel_time"].isna()
    step_removed = (~mask).sum()
    cumulative_removed += step_removed
    df_filtered = df_filtered[mask]
    if debug:
        print(f"Travel time filter - removed {step_removed} (Acum: {cumulative_removed}/{original_total})")

    # --- Hypocentral distance filter ---
    mask = df_filtered["linear_hyp_distance"].between(min_linear_hyp_distance, max_linear_hyp_distance)
    if not apply_to_nans:
        mask |= df_filtered["linear_hyp_distance"].isna()
    step_removed = (~mask).sum()
    cumulative_removed += step_removed
    df_filtered = df_filtered[mask]
    if debug:
        print(f"Hypocentral distance filter - removed {step_removed} (Acum: {cumulative_removed}/{original_total})")

    # --- Epicentral distance filter ---
    mask = df_filtered["distance"].between(min_epicentral_distance, max_epicentral_distance)
    if not apply_to_nans:
        mask |= df_filtered["distance"].isna()
    step_removed = (~mask).sum()
    cumulative_removed += step_removed
    df_filtered = df_filtered[mask]
    if debug:
        print(f"Epicentral distance filter - removed {step_removed} (Acum: {cumulative_removed}/{original_total})")

    # --- S–P threshold filtering ---
    remove_index = set()
    grouped = df_filtered.groupby(["event_id", "station"])

    if debug:
        print(f"S–P QC filter - starting ...")

    for (event_id, station), group in grouped:
        for (s_phase, p_phase), (min_diff, max_diff) in sp_threshold.items():
            phase_norm = df_filtered["phase"].str.strip().str.lower()
            s_rows = group[phase_norm.loc[group.index] == s_phase.lower()]
            p_rows = group[phase_norm.loc[group.index] == p_phase.lower()]

            if s_rows.empty or p_rows.empty:
                continue

            for s_idx, s_row in s_rows.iterrows():
                for p_idx, p_row in p_rows.iterrows():
                    dt = s_row["travel_time"] - p_row["travel_time"]
                    if not (min_diff <= dt <= max_diff):
                        remove_index.update([s_idx, p_idx])
                        if debug:
                            print(
                                f"\tRemoving picks for event {event_id}, station {station}: "
                                f"S_phase {s_row['phase']} (idx={s_idx}) - "
                                f"P_phase {p_row['phase']} (idx={p_idx}), "
                                f"Δt={dt:.2f}s not in [{min_diff}, {max_diff}]"
                            )

    step_removed = len(remove_index)
    cumulative_removed += step_removed
    df_filtered = df_filtered.drop(index=remove_index)
    if debug:
        print(f"S–P QC filter - removed {step_removed} (Acum: {cumulative_removed}/{original_total})")
        print(f"Remaining picks: {len(df_filtered)}")

        # Count NaNs in the QC columns
        nan_counts = df_filtered[["travel_time", "linear_hyp_distance", "distance"]].isna().sum()
        print(
            f"NaNs in remaining picks - travel_time: {nan_counts['travel_time']}, "
            f"distance: {nan_counts['distance']}, "
            f"linear_hyp_distance: {nan_counts['linear_hyp_distance']}"
        )

    return df_filtered.reset_index(drop=True)


def events_qc(
    df,
    min_associated_phase_count=4,
    max_associated_phase_count=None,
    min_used_phase_count=4,
    max_used_phase_count=None,
    min_p_phase_count=0,
    min_s_phase_count=0,
    min_station_count=3,
    max_station_count=None,
    max_standard_error=1.8,
    debug=False,
    apply_to_nans=False,
):
    """
    Apply sequential quality-control (QC) filters to an events DataFrame.

    The following filters are applied in order:

    1. Minimum associated phase count
    2. Maximum associated phase count (optional)
    3. Minimum used phase count
    4. Maximum used phase count (optional)
    5. Minimum P phase count
    6. Minimum S phase count
    7. Minimum station count
    8. Maximum station count (optional)
    9. Maximum standard error
    """

    original_total = len(df)
    cumulative_removed = 0
    df_filtered = df.copy()

    # --- Associated phase count (min) ---
    df_filtered, cumulative_removed = apply_min_filter(
        df_filtered,
        "associated_phase_count",
        min_associated_phase_count,
        "Associated phase count (min)",
        original_total,
        cumulative_removed,
        debug,
        apply_to_nans,
    )

    # --- Associated phase count (max) ---
    if max_associated_phase_count is not None:
        df_filtered, cumulative_removed = apply_max_filter(
            df_filtered,
            "associated_phase_count",
            max_associated_phase_count,
            "Associated phase count (max)",
            original_total,
            cumulative_removed,
            debug,
            apply_to_nans,
        )

    # --- Used phase count (min) ---
    df_filtered, cumulative_removed = apply_min_filter(
        df_filtered,
        "used_phase_count",
        min_used_phase_count,
        "Used phase count (min)",
        original_total,
        cumulative_removed,
        debug,
        apply_to_nans,
    )

    # --- Used phase count (max) ---
    if max_used_phase_count is not None:
        df_filtered, cumulative_removed = apply_max_filter(
            df_filtered,
            "used_phase_count",
            max_used_phase_count,
            "Used phase count (max)",
            original_total,
            cumulative_removed,
            debug,
            apply_to_nans,
        )

    # --- P phase count ---
    df_filtered, cumulative_removed = apply_min_filter(
        df_filtered,
        "p_phase_count",
        min_p_phase_count,
        "P phase count (min)",
        original_total,
        cumulative_removed,
        debug,
        apply_to_nans,
    )

    # --- S phase count ---
    df_filtered, cumulative_removed = apply_min_filter(
        df_filtered,
        "s_phase_count",
        min_s_phase_count,
        "S phase count (min)",
        original_total,
        cumulative_removed,
        debug,
        apply_to_nans,
    )

    # --- Station count (min) ---
    df_filtered, cumulative_removed = apply_min_filter(
        df_filtered,
        "station_count",
        min_station_count,
        "Station count (min)",
        original_total,
        cumulative_removed,
        debug,
        apply_to_nans,
    )

    # --- Station count (max) ---
    if max_station_count is not None:
        df_filtered, cumulative_removed = apply_max_filter(
            df_filtered,
            "station_count",
            max_station_count,
            "Station count (max)",
            original_total,
            cumulative_removed,
            debug,
            apply_to_nans,
        )

    # --- Standard error ---
    df_filtered, cumulative_removed = apply_max_filter(
        df_filtered,
        "standard_error",
        max_standard_error,
        "Standard error (max)",
        original_total,
        cumulative_removed,
        debug,
        apply_to_nans,
    )

    # --- Final summary ---
    if debug:
        remaining = len(df_filtered)
        removed_total = original_total - remaining
        percentage = (
            (removed_total / original_total) * 100
            if original_total > 0
            else 0
        )

        print("\nEvent QC completed:")
        print(
            f"Removed {removed_total}/{original_total} events "
            f"({percentage:.2f}%)"
        )
        print(f"Remaining events: {remaining}")

    return df_filtered.reset_index(drop=True)


def apply_min_filter(df, column, min_value, label,
                     original_total, cumulative_removed,
                     debug=False, apply_to_nans=False):
    """
    Apply a minimum threshold filter to a DataFrame column.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame to filter.
    column : str
        Name of the column to apply the threshold to.
    min_value : float or int
        Minimum allowed value for the column.
    label : str
        Human-readable name of the filter (used in debug output).
    original_total : int
        Original number of rows before QC.
    cumulative_removed : int
        Current cumulative number of removed rows.
    debug : bool, default False
        If True, prints filtering information.
    apply_to_nans : bool, default False
        If True, rows containing NaN in `column` are removed.
        If False, NaN values are ignored.

    Returns
    -------
    df_filtered : pandas.DataFrame
        Filtered DataFrame.
    cumulative_removed : int
        Updated cumulative number of removed rows.
    """
    mask = df[column] >= min_value
    if not apply_to_nans:
        mask |= df[column].isna()

    step_removed = (~mask).sum()
    cumulative_removed += step_removed
    df = df[mask]

    if debug:
        print(f"{label} filter - removed {step_removed} "
              f"(Acum: {cumulative_removed}/{original_total})")

    return df, cumulative_removed


def apply_max_filter(df, column, max_value, label,
                     original_total, cumulative_removed,
                     debug=False, apply_to_nans=False):
    """
    Apply a maximum threshold filter to a DataFrame column.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame to filter.
    column : str
        Name of the column to apply the threshold to.
    max_value : float or int
        Maximum allowed value for the column.
    label : str
        Human-readable name of the filter (used in debug output).
    original_total : int
        Original number of rows before QC.
    cumulative_removed : int
        Current cumulative number of removed rows.
    debug : bool, default False
        If True, prints filtering information.
    apply_to_nans : bool, default False
        If True, rows containing NaN in `column` are removed.
        If False, NaN values are ignored.

    Returns
    -------
    df_filtered : pandas.DataFrame
        Filtered DataFrame.
    cumulative_removed : int
        Updated cumulative number of removed rows.
    """
    mask = df[column] <= max_value
    if not apply_to_nans:
        mask |= df[column].isna()

    step_removed = (~mask).sum()
    cumulative_removed += step_removed
    df = df[mask]

    if debug:
        print(f"{label} filter - removed {step_removed} "
              f"(Acum: {cumulative_removed}/{original_total})")

    return df, cumulative_removed
