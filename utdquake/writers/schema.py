"""
DataFrame sanitization and column type utilities for the dataset.

This module provides functions to:
- Map column names to types.
- Safely sanitize DataFrames for Parquet/Hugging Face.
- Define preferred column types for networks, stations, events, and picks.

Modules:
--------
- pandas
- typing
- obsplus.constants (PICK_DTYPES, EVENT_DTYPES, ARRIVAL_DTYPES)
"""

from __future__ import annotations
from typing import  Optional, Dict, List
from collections import OrderedDict
from obsplus.constants import PICK_DTYPES,EVENT_DTYPES,ARRIVAL_DTYPES   
import pandas as pd


PREF_NETWORK_TYPES = {
    "network": "string",
    "continent": "string",
    "provider": "string",
    "provider_url": "string",
    "country": "string",
    "agency": "string",
    "total_stations": "int64",
    "confirmed_stations": "int64",
    "calculated_stations": "int64",
    "original_events": "int64",
    "original_p_arrivals": "int64",
    "original_s_arrivals": "int64",
    "events": "int64",
    "p_arrivals": "int64",
    "s_arrivals": "int64",
    "start_time": "datetime",
    "end_time": "datetime",
    "approx_lon_min": "float",
    "approx_lon_max": "float",
    "approx_lat_min": "float",
    "approx_lat_max": "float",
    "score": "float",
}

PREF_NETWORK_ORDER = list(PREF_NETWORK_TYPES.keys())


PREF_STATIONS_TYPES = {"network": "string",
                        "station": "string",
                        "available": "boolean",
                        "confirmed": "boolean",
                        "confirmed_latitude": "float",
                        "confirmed_longitude": "float",
                        "calculated": "boolean",
                        "calculated_latitude": "float",
                        "calculated_latitude_std": "float",
                        "calculated_longitude": "float",
                        "calculated_longitude_std": "float",
                        "confirmed_elevation": "float",
                        "calculated_num_entries": "int64",
                        "db_path": "string",
                        "creation_time": "datetime"
                        }
PREF_STATIONS_ORDER = list(PREF_STATIONS_TYPES.keys())

PREF_EVENTS_ORDER = ["network",
                     "time",
                    "latitude",
                    "longitude",
                    "depth",
                    "magnitude",
                    "azimuthal_gap"]

PREF_PICKS_ORDER = [
                    "network",
                    "station", 
                    "phase",
                    "time",
                    "travel_time",
                    "travel_time_zscore",
                    "distance",
                    "linear_hyp_distance",
                    "azimuth",
                    "evaluation_mode",
                    "event_id",
                    "origin_time",
                    ]


def columns_by_type(dtypes: Dict[str, object]) -> Dict[str, List[str]]:
    """
    Group column names by their data type.

    Given a dictionary of column_name -> dtype (string or Python type),
    returns a dictionary with lists of columns grouped by type:
    'string', 'float', 'int', 'datetime', 'boolean'.

    Args
    ----
    dtypes : Dict[str, object]
        Mapping of column names to their data types (str or Python type).

    Returns
    -------
    Dict[str, List[str]]
        Dictionary containing lists of column names for each type:
        'string_cols', 'float_cols', 'int_cols', 'datetime_cols', 'bool_cols'.
    """
    string_cols = []
    float_cols = []
    int_cols = []
    datetime_cols = []
    bool_cols = []

    for col, dtype in dtypes.items():
        # Normalize string representations to lowercase
        if isinstance(dtype, str):
            dtype_lower = dtype.lower()
            if dtype_lower in ("str", "string","nslc_code"):
                string_cols.append(col)
            elif dtype_lower in ("float", "float64"):
                float_cols.append(col)
            elif dtype_lower in ("int", "int64"):
                int_cols.append(col)
            elif dtype_lower in ("datetime", "datetime64", "datetime64[ns]",
                                  "timestamp"):
                datetime_cols.append(col)
            elif dtype_lower in ("bool", "boolean"):
                bool_cols.append(col)
        else:
            # dtype is actual Python type
            if dtype is str:
                string_cols.append(col)
            elif dtype in (float, "float64"):  # sometimes float64
                float_cols.append(col)
            elif dtype in (int, "int64"):
                int_cols.append(col)
            elif dtype in (pd.Timestamp, "datetime64[ns]"):
                datetime_cols.append(col)
            elif dtype is bool:
                bool_cols.append(col)

    return {
        "string_cols": string_cols,
        "float_cols": float_cols,
        "int_cols": int_cols,
        "datetime_cols": datetime_cols,
        "bool_cols": bool_cols,
    }


# Convert preferred types to grouped column lists
PREF_NETWORK_TYPES = columns_by_type(PREF_NETWORK_TYPES)
PREF_STATIONS_TYPES = columns_by_type(PREF_STATIONS_TYPES)
PREF_PICKS_TYPES = columns_by_type(PICK_DTYPES)
PREF_ARRIVALS_TYPES = columns_by_type(ARRIVAL_DTYPES)

QC_DTYPES = OrderedDict([('travel_time_zscore',float)])
PREF_PICKS_QC_TYPES = columns_by_type(QC_DTYPES)

# Merge arrival types into picks
for k,v in PREF_ARRIVALS_TYPES.items():
    PREF_PICKS_TYPES[k].extend(v)

for k,v in PREF_PICKS_QC_TYPES.items():
    PREF_PICKS_TYPES[k].extend(v)

# Add extra columns to picks types
PREF_PICKS_TYPES["string_cols"].extend(["network","event_id",])
PREF_PICKS_TYPES["float_cols"].extend(["travel_time","linear_hyp_distance"])

# Preferred event types
PREF_EVENTS_TYPES = columns_by_type(EVENT_DTYPES)
PREF_EVENTS_TYPES["string_cols"].extend(["network","prefered_origin_id"])


def order_dataframe_columns(df: pd.DataFrame, preferred_order: List[str]) -> pd.DataFrame:
    """
    Reorder the columns of a DataFrame according to a preferred order.

    Columns listed in `preferred_order` appear first in the resulting DataFrame,
    in the specified sequence. Columns not listed in `preferred_order` are appended
    after the preferred columns, maintaining their original order.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame whose columns should be reordered.
    preferred_order : list[str] or str
        List of column names specifying the desired order. Alternatively, a string
        key can be provided to use predefined orderings:
        - "network" → uses PREF_NETWORK_ORDER
        - "events" → uses PREF_EVENTS_ORDER
        - "picks" → uses PREF_PICKS_ORDER

    Returns
    -------
    pd.DataFrame
        A new DataFrame with columns reordered.

    Raises
    ------
    ValueError
        If `preferred_order` is not a recognized string key or list of column names.

    Examples
    --------
    >>> df = pd.DataFrame({"b": [1], "a": [2], "c": [3]})
    >>> order_dataframe_columns(df, ["a", "b"])
       a  b  c
    0  2  1  3
    """
    if isinstance(preferred_order, str):
        if preferred_order == "network":
            preferred_order = PREF_NETWORK_ORDER
        if preferred_order == "events":
            preferred_order = PREF_EVENTS_ORDER
        elif preferred_order == "picks":
            preferred_order = PREF_PICKS_ORDER
        else:
            raise ValueError(f"Unknown preferred order: {preferred_order}")
    elif not isinstance(preferred_order, list):
        raise ValueError("preferred_order must be a list of column names or a recognized string key")

    existing_pref = [c for c in preferred_order if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_pref]
    df = df[existing_pref + remaining]
    return df

def sanitize_dataframe(
    df: pd.DataFrame,
    string_cols: Optional[List[str]] = None,
    float_cols: Optional[List[str]] = None,
    int_cols: Optional[List[str]] = None,
    datetime_cols: Optional[List[str]] = None,
    bool_cols: Optional[List[str]] = None,
    order_cols: Optional[List[str]] = None,
    debug: bool = False
) -> pd.DataFrame:
    """
    Safely sanitize a DataFrame for Parquet / Hugging Face Datasets.

    Ensures proper data types and formatting, including:
    - Normalizing column names.
    - Converting columns to specified dtypes.
    - Handling object columns safely.
    - Ensuring nullable integers and booleans for Arrow compatibility.

    Args
    ----
    df : pd.DataFrame
        Input DataFrame.
    string_cols : list[str], optional
        Columns to force as strings.
    float_cols : list[str], optional
        Columns to force as floats.
    int_cols : list[str], optional
        Columns to force as integers.
    datetime_cols : list[str], optional
        Columns to force as datetime.
    bool_cols : list[str], optional
        Columns to force as boolean.
    order_cols : list[str], optional
        Preferred column order (columns in this list will be ordered first).
    debug : bool, optional
        If True, prints DataFrame state at each step (default False).

    Returns
    -------
    pd.DataFrame
        Sanitized DataFrame ready for Parquet/Hugging Face storage.
    """
    df = df.copy()

    string_cols = list(set(string_cols)) if string_cols else []
    float_cols = list(set(float_cols)) if float_cols else []
    int_cols = list(set(int_cols)) if int_cols else []
    datetime_cols = list(set(datetime_cols)) if datetime_cols else []
    bool_cols = list(set(bool_cols)) if bool_cols else []
    
    if debug:
        print("Step 0: Original DataFrame")
        print(df.head(), "\n")
        print("Dtypes:", df.dtypes, "\n")
    
    # ---- 1. Normalize column names ----
    df.columns = df.columns.str.lower().str.replace(r"\s+", "_", 
                                                    regex=True)
    if debug:
        print("Step 1: Normalized column names")
        print(df.head(), "\n")
    
    # ---- 2. Parse datetime columns ----
    if datetime_cols:
        for c in datetime_cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    # else:
    #     for c in df.select_dtypes(include=["object"]).columns:
    #         try:
    #             df[c] = pd.to_datetime(df[c], errors="ignore")
    #             msg = f"Auto-converted column '{c}' to datetime (if possible)"
    #         except Exception:
    #             msg = f"Column '{c}' could not be auto-converted to datetime"
    #             pass
    #         if debug:
    #             print(msg)
    if debug:
        print("Step 2: After datetime conversion")
        print(df.head(), "\n")
    
    # ---- 3. Force float columns ----
    if float_cols:
        for c in float_cols:
            # if c not in df.columns:
            #     continue

            # #  skip datetime columns
            # if pd.api.types.is_datetime64_any_dtype(df[c]):
            #     continue
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    if debug and float_cols:
        print(f"Step 3: Forced float columns: {float_cols}")
        print(df.head(), "\n")
    
    # ---- 4. Force integer columns ----
    if int_cols:
        for c in int_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")  # nullable int
    if debug and int_cols:
        print(df.head(), "\n")
        print(f"Step 4: Forced integer columns: {int_cols}")
    
    # ---- 5. Force string columns ----
    if string_cols:
        for c in string_cols:
            if c in df.columns:
                df[c] = df[c].astype("string")
    if debug and string_cols:
        print(f"Step 5: Forced string columns: {string_cols}")
    
    # ---- 6. Force boolean columns ----
    if bool_cols:
        for c in bool_cols:
            if c in df.columns:
                df[c] = df[c].astype("boolean")
    if debug and bool_cols:
        print(f"Step 6: Forced boolean columns: {bool_cols}")
    
    # ---- 7. Auto-handle remaining object columns ----
    for c in df.select_dtypes(include=["object"]).columns:
        df[c] = df[c].astype("string")
    
    # ---- 8. Numeric columns → float64 for Arrow safety ----
    for c in df.select_dtypes(include=["float64"]).columns:
        df[c] = df[c].astype("float64")

    for c in df.select_dtypes(include=["int64", "Int64"]).columns:
        df[c] = df[c].astype("Int64")
    
    # ---- 9. Boolean → nullable boolean (catch any remaining) ----
    for c in df.select_dtypes(include=["bool"]).columns:
        df[c] = df[c].astype("boolean")
    
    if order_cols is not None:
        df = order_dataframe_columns(df, order_cols)


    if debug:
        print("Step 7-9: Final DataFrame after sanitization")
        print(df.head(), "\n")
        print("Dtypes after sanitization:")
        print(df.dtypes)
        print("\nDescriptive statistics:")
        print(df.describe())


    return df
