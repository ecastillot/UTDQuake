import numpy as np
import pandas as pd
from .log import QCLog

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
    log=None,
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

    if log is None:
        log = QCLog()

    original_total = len(df)
    df_filtered = df.copy()

    # Helper function to apply min filter
    def apply_min(df, col, value, label):
        mask = df[col] >= value
        if not apply_to_nans:
            mask |= df[col].isna()
        removed = (~mask).sum()
        df_filtered_step = df[mask]
        log.add_step(label, removed, thresholds={"min": value})
        if debug:
            print(f"{label} filter - removed {removed} "
                  f"(Cumulative: {log.cumulative_removed}/{original_total})")
        return df_filtered_step

    # Helper function to apply max filter
    def apply_max(df, col, value, label):
        mask = df[col] <= value
        if not apply_to_nans:
            mask |= df[col].isna()
        removed = (~mask).sum()
        df_filtered_step = df[mask]
        log.add_step(label, removed, thresholds={"max": value})
        if debug:
            print(f"{label} filter - removed {removed} "
                  f"(Cumulative: {log.cumulative_removed}/{original_total})")
        return df_filtered_step

    # --- Associated phase count ---
    df_filtered = apply_min(df_filtered, "associated_phase_count", min_associated_phase_count, "associated_phase_count_min")
    if max_associated_phase_count is not None:
        df_filtered = apply_max(df_filtered, "associated_phase_count", max_associated_phase_count, "associated_phase_count_max")

    # --- Used phase count ---
    df_filtered = apply_min(df_filtered, "used_phase_count", min_used_phase_count, "used_phase_count_min")
    if max_used_phase_count is not None:
        df_filtered = apply_max(df_filtered, "used_phase_count", max_used_phase_count, "used_phase_count_max")
    
    # --- P and S phase count ---
    df_filtered = apply_min(df_filtered, "p_phase_count", min_p_phase_count, "p_phase_count_min")
    df_filtered = apply_min(df_filtered, "s_phase_count", min_s_phase_count, "s_phase_count_min")

    # --- Station count ---
    df_filtered = apply_min(df_filtered, "station_count", min_station_count, "station_count_min")
    if max_station_count is not None:
        df_filtered = apply_max(df_filtered, "station_count", max_station_count, "station_count_max")

    # --- Standard error ---
    df_filtered = apply_max(df_filtered, "standard_error", max_standard_error, "standard_error_max")

    # --- Final summary ---
    if debug:
        remaining = len(df_filtered)
        removed_total = original_total - remaining
        percentage = (removed_total / original_total) * 100 if original_total > 0 else 0
        print("\nEvent QC completed:")
        print(f"Removed {removed_total}/{original_total} events ({percentage:.2f}%)")
        print(f"Remaining events: {remaining}")

    return df_filtered.reset_index(drop=True), log


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