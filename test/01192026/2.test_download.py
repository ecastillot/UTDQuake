# import os
# os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

import utdquake as utdq
from obspy import UTCDateTime
from utdquake.bank.bank import EventBank  
import utdquake.bank.utils as fut

from utdquake.core.download import download_utdquake


import utdquake as utdq
import pandas as pd

from utdquake.core.cache import _append_fdsn_info
import time
import logging
from utdquake.bank.bank import EventBank
from utdquake.core.manifest import sanitize_dataframe_for_parquet
from utdquake.core.config import (PREF_PICKS_ORDER,PREF_EVENTS_ORDER,
                                  PREF_STATIONS_ORDER,PREF_STATS_ORDER,
                                  PREF_PICKS_TYPES,PREF_EVENTS_TYPES,
                                  PREF_STATIONS_TYPES,PREF_STATS_TYPES)
import datetime as dt
logging.basicConfig(
    level=logging.INFO,  # or DEBUG for more details
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# net = "RSNC"
# bank = EventBank(f"/groups/igonin/ecastillo/UTDQuake/events/{net}")

# events = bank.read_index()
# events = events[events["time"] >= dt.datetime(2024, 11,8,23,50,0)]
# events = events[events["time"] < dt.datetime(2024, 11, 9)]

# ev_ids = events["event_id"].tolist()
# events = bank.get_events(event_id=ev_ids)
# event = events[0]
# arrival = event.arrivals_to_df()
# picks = event.picks_to_df()
# # print(arrival["pick_id"])
# # print(picks["resource_id"])
# # exit()
# arrival = pd.merge(arrival,picks,left_on="pick_id",right_on="resource_id",
#                    how="left",)

# arrival["travel_time"] = (arrival["time"] - arrival["origin_time"]).dt.total_seconds()
# arrival = arrival[arrival["travel_time"]<0]
# print(arrival)
# # print(events)
# print(arrival[["station_x","time","phase","origin_time"]])
# exit()

# events = bank.get_events(starttime=UTCDateTime("2023-01-01T00:00:00"),
#                         endtime=UTCDateTime("2023-12-31T23:59:59"))


# net = "AEIC"
# bank = EventBank(f"/groups/igonin/ecastillo/UTDQuake/events/{net}")
# picks = bank.load_picks()

# picks["tt"] = (picks["time"]-picks["origin_time"]).dt.total_seconds()

# picks = sanitize_dataframe_for_parquet(picks,
#                                        string_cols=PREF_PICKS_TYPES["string_cols"],
#                                                 float_cols=PREF_PICKS_TYPES["float_cols"],
#                                                 int_cols=PREF_PICKS_TYPES["int_cols"],
#                                                 datetime_cols=PREF_PICKS_TYPES["datetime_cols"],
#                                                 bool_cols=PREF_PICKS_TYPES["bool_cols"],
#                                                 debug=True)
# path = f"/groups/igonin/ecastillo/UTDQuake/manifests/picks/network={net}.parquet"
# picks.to_parquet(path)
# print(picks["time_correction"])

# print(PREF_PICKS_TYPES)
# exit()



# print(bank)

# exit()

# # # loads tx
# bank =  utdq.load_network("AEIC") 
# picks = bank.load_picks()
# print(picks)
# exit()

# df_stats = pd.DataFrame([bank.stats])
# df_stats["network"] = df_stats["Contributor"]

# include_manual_network_info  = pd.read_csv("/groups/igonin/ecastillo/utdquake/utdquake/core/manual_info.csv")
# df_stats = pd.merge(df_stats,include_manual_network_info,
#                                     on="network",how="left")
# df_stats.columns = df_stats.columns.str.lower()
# df_stats.columns = df_stats.columns.str.replace(r"\s+", "_", regex=True)
# print(df_stats.info())

# stations = bank.get_stations()
# print(stations.info())

# picks = bank.load_picks(fmt="sql")
# print(picks)

# print(bank.read_index()["event_id"].head())
# event_ids = bank.read_index()["event_id"].tolist()

# tic = time.time()
# picks = bank.get_picks(event_ids[:100])
# toc = time.time()
# print(picks)
# print(f"Time to get picks for 100 events: {toc - tic:.2f} seconds")


stats = pd.DataFrame([bank.stats])
stats = _append_fdsn_info(stats)
events = bank.read_index()
stations = bank.get_stations()
events.columns = ["source_" + col for col in events.columns]
stations.columns = ["station_" + col for col in stations.columns]


try:
    picks = bank.load_picks()
    picks["tt"] = (picks["time"]-picks["origin_time"]).dt.total_seconds()
    picks.columns = ["pick_" + col for col in picks.columns]
except Exception as e:
    picks = pd.DataFrame()


# print(picks.info())
# print(events.info())
# print(stations.info())
# exit()

data = [events, stations, picks]
# clean empty dataframes
data = [df for df in data if not df.empty]
data = pd.concat(data, axis=1)


def flatten_stats(df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    """
    Flatten df.describe() to a single row with only min, max, mean, std.
    Works for all numeric columns. Datetimes are ignored (optional to add).

    Parameters
    ----------
    df : pd.DataFrame
        Original DataFrame.
    prefix : str
        Optional prefix for column names.

    Returns
    -------
    pd.DataFrame
        Single-row DataFrame with flattened stats.
    """
    # Only numeric columns
    # numeric_df = df.select_dtypes(include="number")
    numeric_df = df.select_dtypes(include=["number", "datetime64[ns]"])
    
    # Describe numeric columns (fast)
    desc = numeric_df.describe().T  # transpose
    
    # Keep only min, max, mean, std
    desc = desc[["min", "max", "mean", "std"]]
    
    # Flatten into single row
    flat_dict = {}
    for col in desc.index:
        for stat in desc.columns:
            flat_dict[f"{prefix}{col}_{stat}"] = desc.loc[col, stat]
    
    return pd.DataFrame([flat_dict])

data = flatten_stats(data)
print(data.columns)
# flat_stats = flatten_describe(data)
# flat_stats.to_csv("/groups/igonin/ecastillo/utdquake/test/01192026/report/tx_report.csv", index=False)
# print(flat_stats)
# flat_stats.columns = [f"{col}_{stat}" if col != "index" else "column_name" 
#                       for col, stat in zip(flat_stats["column_name"], flat_stats.columns[1:])]

# print(flat_stats.columns)

# print(events.info())
# print(events.describe())
# print(stations.describe())

# print(events.describe().info())
# picks = bank.load_picks()

# print(picks.describe())
# print(picks.describe().columns)
# print(bank.load_picks())


# x = _append_fdsn_info(stats)
# print(x)
# print(df)
# print(bank.stats)

# # get Obspy Catalog
# catalog = bank.get_events(starttime=UTCDateTime("2025-07-31T00:00:00"), 
#                             endtime=UTCDateTime("2025-07-31T12:00:00"))
# print(catalog)

# # get dataframes
# catalog.to_df()
# catalog[0].picks_to_df()
# catalog[0].arrivals_to_df()

# test = "/groups/igonin/ecastillo/test_u"
# download_utdquake(local_dir=test,networks="*")


# test = "/groups/igonin/ecastillo/UTDQuake/events/av/.index.db"
# x = fut.get_table_names(test)
# print(x)


# bank =  utdq.load_network("nc")
# print(bank)
# print(bank.__str__(True))
# print(bank.bank_path)
# print(bank.picks_table_names)
# print(bank.stats)
# events = bank.read_index()
# # print(bank.picks_path)
# # # print(events[['event_id','time']])
# x = bank.save_picks()
# x = bank.get_picks()
# print(x)


# print(bank.get_stations())

# x = bank.get_stations_details()

# bank.plot_overview(savepath= "/groups/igonin/ecastillo/utdquake/test/01192026/test.png")
# x = bank._get_picks_from_chunk(event_ids=["smi:ISC/evid=643989876"])
# catalog = bank.get_events(starttime=UTCDateTime("2025-07-31T00:00:00"), 
#                 endtime=UTCDateTime("2025-07-31T12:00:00"))
# print(catalog)
# print(f"Number of events downloaded: {len(events)}")