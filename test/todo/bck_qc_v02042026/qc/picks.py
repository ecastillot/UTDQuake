import numpy as np
import pandas as pd
from .log import QCLog


def basic_picks_qc(
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
    log=None,
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

    if log is None:
        log = QCLog()

    original_total = len(df)
    df_filtered = df.copy()

    # --- Travel time filter ---
    mask = df_filtered["travel_time"].between(min_travel_time, max_travel_time)
    if not apply_to_nans:
        mask |= df_filtered["travel_time"].isna()
    step_removed = (~mask).sum()
    df_filtered = df_filtered[mask]
    log.add_step("travel_time_filter", step_removed, thresholds={"min": min_travel_time, "max": max_travel_time})
    if debug:
        print(f"Travel time filter - removed {step_removed} (Cumulative: {log.cumulative_removed}/{original_total})")


    # --- Hypocentral distance filter ---
    mask = df_filtered["linear_hyp_distance"].between(min_linear_hyp_distance, max_linear_hyp_distance)
    if not apply_to_nans:
        mask |= df_filtered["linear_hyp_distance"].isna()
    step_removed = (~mask).sum()
    df_filtered = df_filtered[mask]
    log.add_step("hypocentral_distance_filter", step_removed, thresholds={"min": min_linear_hyp_distance, "max": max_linear_hyp_distance})
    if debug:
        print(f"Hypocentral distance filter - removed {step_removed} (Cumulative: {log.cumulative_removed}/{original_total})")

    # --- Epicentral distance filter ---
    mask = df_filtered["distance"].between(min_epicentral_distance, max_epicentral_distance)
    if not apply_to_nans:
        mask |= df_filtered["distance"].isna()
    step_removed = (~mask).sum()
    df_filtered = df_filtered[mask]
    log.add_step("epicentral_distance_filter", step_removed, thresholds={"min": min_epicentral_distance, "max": max_epicentral_distance})
    if debug:
        print(f"Epicentral distance filter - removed {step_removed} (Cumulative: {log.cumulative_removed}/{original_total})")

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
    df_filtered = df_filtered.drop(index=remove_index)
    log.add_step("sp_threshold_filter", step_removed, thresholds=sp_threshold)
    if debug:
        print(f"S–P QC filter - removed {step_removed} (Cumulative: {log.cumulative_removed}/{original_total})")
        print(f"Remaining picks: {len(df_filtered)}")

        # Count NaNs in the QC columns
        nan_counts = df_filtered[["travel_time", "linear_hyp_distance", "distance"]].isna().sum()
        print(
            f"NaNs in remaining picks - travel_time: {nan_counts['travel_time']}, "
            f"distance: {nan_counts['distance']}, "
            f"linear_hyp_distance: {nan_counts['linear_hyp_distance']}"
        )

    return df_filtered.reset_index(drop=True), log
