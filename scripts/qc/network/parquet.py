from __future__ import annotations
import pandas as pd
# read the parquet file
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
import pandas as pd

path = "/groups/igonin/ecastillo/utdquake/scripts/qc/network/network_hf.parquet"
df_ori = pd.read_parquet(path)
print(df_ori.info())

path_cor = "/groups/igonin/ecastillo/utdquake/scripts/qc/network/network_cor.csv"
df_cor = pd.read_csv(path_cor)
print(df_cor.info())


cor_cols = ["network","agency","continent","url","score"]
df_cor = df_cor[cor_cols]   
df_cor = df_cor.rename(columns={"agency": "provider"})

gd_label_df = pd.read_csv("/groups/igonin/ecastillo/utdquake/scripts/qc/network/network_name_country.csv")

df_cor = pd.merge(df_cor, gd_label_df, on="network", how="left")
print(df_cor.info())

df_ori = pd.merge(df_ori, df_cor, on="network", how="left", suffixes=("_ori", "_cor"))

alaska_region = (-180, -130, 50, 72)  
alaska_netwroks = ["av","ak","AEIC"]

# locate alaska networks and change the approx_lon_min, approx_lon_max, approx_lat_min, approx_lat_max to the alaska region
for network in alaska_netwroks:
    mask = df_ori["network"] == network
    df_ori.loc[mask, "approx_lon_min"] = alaska_region[0]
    df_ori.loc[mask, "approx_lon_max"] = alaska_region[1]
    df_ori.loc[mask, "approx_lat_min"] = alaska_region[2]
    df_ori.loc[mask, "approx_lat_max"] = alaska_region[3]


df_ori.drop_duplicates(subset=["network"], inplace=True)

df_ori.rename(columns={"url": "provider_url"}, inplace=True)
df_ori.drop(columns=["contributor"], inplace=True)

print(df_ori.info())

#first columns
first_cols = ["network","continent", "provider", "provider_url","country","agency","events"]

cols = df_ori.columns.tolist()
# move the first columns to the beginning of the dataframe
for col in reversed(first_cols):
    cols.insert(0, cols.pop(cols.index(col)))
df_ori= df_ori[cols]  # reorder the dataframe
df_ori["country"] = df_ori["country"].fillna("Unknown")


#to_parquet
PREF_STATS_TYPES = {
    "network": "string",
    "continent": "string",
    "provider": "string",
    "provider_url": "string",
    "country": "string",
    "agency": "string",
    "events": "int64",
    "total_stations": "int64",
    "confirmed_stations": "int64",
    "calculated_stations": "int64",
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

def columns_by_type(dtypes: Dict[str, object]) -> Dict[str, List[str]]:
    """
    Given a dict of column_name -> dtype (string or Python type),
    returns a dict of lists of columns grouped by type:
    'string', 'float', 'int', 'datetime', 'boolean'.
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

def sanitize_dataframe_for_parquet(
    df: pd.DataFrame,
    string_cols=None,
    float_cols=None,
    int_cols=None,
    datetime_cols=None,
    bool_cols=None,
    debug=False
) -> pd.DataFrame:
    """
    Safely sanitize a DataFrame for Parquet / Hugging Face Datasets.

    Args:
        df (pd.DataFrame): Input DataFrame
        string_cols (list[str], optional): Columns to force as strings
        float_cols (list[str], optional): Columns to force as floats
        int_cols (list[str], optional): Columns to force as integers
        datetime_cols (list[str], optional): Columns to force as datetime
        bool_cols (list[str], optional): Columns to force as boolean
        debug (bool): If True, prints DataFrame state at each step

    Returns:
        pd.DataFrame: Sanitized DataFrame
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
    df.columns = df.columns.str.lower().str.replace(r"\s+", "_", regex=True)
    if debug:
        print("Step 1: Normalized column names")
        print(df.head(), "\n")
    
    # ---- 2. Parse datetime columns ----
    if datetime_cols:
        for c in datetime_cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    else:
        for c in df.select_dtypes(include=["object"]).columns:
            try:
                df[c] = pd.to_datetime(df[c], errors="ignore")
            except Exception:
                pass
    if debug:
        print("Step 2: After datetime conversion")
        print(df.head(), "\n")
    
    # ---- 3. Force float columns ----
    if float_cols:
        for c in float_cols:
            # if c not in df.columns:
            #     continue

            # # 🚫 skip datetime columns
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
    
    if debug:
        print("Step 7-9: Final DataFrame after sanitization")
        print(df.head(), "\n")
        print("Dtypes after sanitization:")
        print(df.dtypes)
        print("\nDescriptive statistics:")
        print(df.describe())

    return df

PREF_STATS_TYPES = columns_by_type(PREF_STATS_TYPES)
df_ori = sanitize_dataframe_for_parquet(df_ori, **PREF_STATS_TYPES, debug=True)
print(df_ori.info())
df_ori.to_parquet("/groups/igonin/ecastillo/utdquake/scripts/qc/network/network.parquet", index=False)
df_ori.to_csv("/groups/igonin/ecastillo/utdquake/scripts/qc/network/check_network.csv", index=False)