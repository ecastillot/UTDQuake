from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
import pandas as pd
from obsplus.constants import PICK_DTYPES,EVENT_DTYPES,ARRIVAL_DTYPES   

DEFAULT_REPO_ID = "ecastillot/UTDQuake"
DEFAULT_REPO_TYPE = "dataset"
ENV_CACHE_ROOT = "UTDQUAKE_ROOT"
ENV_UTDQUAKE_MANUAL_INFO = "UTDQUAKE_MANUAL_INFO"

CORE_DIR = Path(__file__).resolve().parent


PREF_PICKS_ORDER = [
                    "network",
                    "station",  # or "sta"
                    "phase",
                    "travel_time",
                    "azimuth",
                    "distance",
                    "time",
                    "event_id",
                    "origin_time",
                    ]

PREF_EVENTS_ORDER = ["network",
                     "time",
                    "latitude",
                    "longitude",
                    "depth",
                    "magnitude",
                    "azimuthal_gap"]

PREF_STATIONS_ORDER = ["network",
                        "station",  # or "sta"
                        "available",
                        "confirmed",
                        "confirmed_latitude",
                        "confirmed_longitude",
                        "confirmed_elevation",
                        "calculated",
                        "calculated_latitude",
                        "calculated_longitude",
                        "calculated_latitude_std",
                        "calculated_longitude_std",
                        "calculated_num_entries"
                        "db_path",
                        "creation_time"
                        ]

PREF_STATS_ORDER = ["network",
                    "agency",
                    "continent",
                    "events",
                    "total_stations",
                    "confirmed_stations",
                    "calculated_stations",
                    "p_arrivals",
                    "s_arrivals",
                    "start_time",
                    "end_time",
                    "url"]
                    




# PREF_EVENTS_TYPES = {
#     "network": "string",
#     "time": "datetime",
#     "latitude": "float",
#     "longitude": "float",
#     "depth": "float",
#     "magnitude": "float",
#     "azimuthal_gap": "float",
# }

# PREF_STATIONS_TYPES = {
#     "network": "string",
#     "station": "string",
#     "available": "boolean",
#     "confirmed": "boolean",
#     "confirmed_latitude": "float",
#     "confirmed_longitude": "float",
#     "calculated": "boolean",
#     "calculated_latitude": "float",
#     "calculated_longitude": "float",
# }



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


PREF_PICKS_TYPES = columns_by_type(PICK_DTYPES)
PREF_ARRIVALS_TYPES = columns_by_type(ARRIVAL_DTYPES)

for k,v in PREF_ARRIVALS_TYPES.items():
    PREF_PICKS_TYPES[k].extend(v)
PREF_PICKS_TYPES["string_cols"].extend(["network"])
PREF_PICKS_TYPES["float_cols"].extend(["travel_time"])

PREF_EVENTS_TYPES = columns_by_type(EVENT_DTYPES)
PREF_EVENTS_TYPES["string_cols"].extend(["network"])

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

PREF_STATIONS_TYPES = columns_by_type(PREF_STATIONS_TYPES)


PREF_STATS_TYPES = {
    "network": "string",
    "agency": "string",
    "continent": "string",
    "events": "int64",
    "total_stations": "int64",
    "confirmed_stations": "int64",
    "calculated_stations": "int64",
    "p_arrivals": "int64",
    "s_arrivals": "int64",
    "start_time": "datetime",
    "end_time": "datetime",
    "url": "string",
    "approx_lon_min": "float",
    "approx_lon_max": "float",
    "approx_lat_min": "float",
    "approx_lat_max": "float",
    "score": "float",
    "countries": "string",
}
PREF_STATS_TYPES = columns_by_type(PREF_STATS_TYPES)

@dataclass(frozen=True)
class UTDQuakeConfig:
    repo_id: str = DEFAULT_REPO_ID
    repo_type: str = DEFAULT_REPO_TYPE
    env_cache_root: str = ENV_CACHE_ROOT
