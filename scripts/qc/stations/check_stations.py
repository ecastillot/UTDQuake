import os
import glob
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from obspy import UTCDateTime
import concurrent.futures as cf
import logging
import datetime

logger = logging.getLogger(__name__)


def _load_station_dataframe(db_path, creation_starttime, creation_endtime, drop_duplicates):
    """Load station index table from SQLite and apply filters."""

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM '/stations/index'",
            conn,
            parse_dates=["creation_time"]
        )

    bool_cols = ["available", "confirmed", "calculated", "used"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    if creation_starttime is not None:
        df = df[pd.to_datetime(df["creation_time"]) >= pd.to_datetime(creation_starttime)]

    if creation_endtime is not None:
        df = df[pd.to_datetime(df["creation_time"]) <= pd.to_datetime(creation_endtime)]

    if drop_duplicates:
        df = df.drop_duplicates(
            subset=["network", "station", "origin_id"],
            ignore_index=True
        )

    return df


def _collapse_dataframe(df: pd.DataFrame) -> dict:
    """Reduce a station dataframe into a single summary dictionary."""

    summary = {}
    exclude_cols = {"dist_deg", "esaz", "used", "origin_id", "creation_time"}

    for col in df.columns:
        if col in exclude_cols:
            continue

        series = df[col]

        if pd.api.types.is_float_dtype(series):
            summary[col] = series.mean()
            if "calculated" in col:
                summary[f"{col}_std"] = series.std()

        elif pd.api.types.is_bool_dtype(series):
            summary[col] = series.any()

        elif pd.api.types.is_integer_dtype(series):
            summary[col] = series.max()
            if "calculated" in col:
                summary[f"{col}_std"] = series.std()

        elif col in ["network", "station"]:
            summary[col] = ",".join(series.unique())

        else:
            summary[col] = series.iloc[0]

    return summary


def _apply_thresholds(summary: dict, min_std: float, min_num_entries: int) -> dict:
    """Invalidate calculated results if they do not meet quality thresholds."""

    num_entries = summary.get("calculated_num_entries", 0)

    if num_entries < min_num_entries:
        summary["calculated"] = False

    for key in ["calculated_latitude", "calculated_longitude"]:
        std_key = f"{key}_std"

        if std_key in summary:
            std_val = summary.get(std_key)

            if std_val is None or (not pd.isna(std_val) and std_val > min_std):
                summary["calculated"] = False

    if not summary.get("calculated", False):
        for key in [
            "calculated_latitude",
            "calculated_longitude",
            "calculated_latitude_std",
            "calculated_longitude_std",
            "calculated_num_entries",
        ]:
            summary[key] = np.nan

    return summary


def _relative_db_path(db_path: str) -> str:
    """Extract relative path after the 'bank' directory."""

    full_path = Path(db_path)

    try:
        relative = full_path.parts[full_path.parts.index("bank") + 1 :]
        return "/".join(relative)
    except ValueError:
        return str(full_path)


def _process_single_db(
    db_path,
    creation_starttime,
    creation_endtime,
    drop_duplicates,
    min_std,
    min_num_entries,
):
    """Process a single database file and return its summary."""

    df = _load_station_dataframe(
        db_path,
        creation_starttime,
        creation_endtime,
        drop_duplicates,
    )

    if df.empty:
        return None

    summary = _collapse_dataframe(df)

    summary["calculated_num_entries"] = int(len(df))
    summary["db_path"] = _relative_db_path(db_path)
    summary["creation_time"] = UTCDateTime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    summary = _apply_thresholds(summary, min_std, min_num_entries)

    return summary


def get_stations_summary(
    stations_folder,
    creation_starttime=None,
    creation_endtime=None,
    drop_duplicates=True,
    min_std=0.1,
    min_num_entries=10,
):

    stations_paths = glob.glob(
        os.path.join(stations_folder, ".**.db"),
        recursive=True
    )

    logger.info(
        f"Found {len(stations_paths)} station databases in {stations_folder}."
    )

    with cf.ThreadPoolExecutor(max_workers=None) as executor:
        results = executor.map(
            lambda path: _process_single_db(
                path,
                creation_starttime,
                creation_endtime,
                drop_duplicates,
                min_std,
                min_num_entries,
            ),
            stations_paths,
        )

    summaries = [r for r in results if r is not None]

    return pd.DataFrame(summaries)

def replace_stations_summary_to_bank(summary, bank_path):

    ebank_index_path = os.path.join(bank_path, ".index.db")

    if summary is not None:
        logger.info(f"Updating stations summary in the event bank at {bank_path}")
        with sqlite3.connect(ebank_index_path) as ev_con:
            summary.to_sql(
                            "/stations/index", ev_con, 
                            if_exists='replace', index=False
                        )
            
            now = datetime.datetime.now().timestamp()

            # put it in a dataframe
            df = pd.DataFrame({"last_updated": [now]})
            df.to_sql(
                    "/stations/last_updated", ev_con,
                    if_exists="replace", index=False
                )
        logger.info(f"Stations summary updated successfully.")

def replace_stations_to_multiple_banks(parent_folder):

    bank_folders = [f.path for f in os.scandir(parent_folder) if f.is_dir()]

    for bank_path in bank_folders:
        print(f"Processing bank at {bank_path}")
        stations_folder = os.path.join(bank_path,".stations")
        print(f"Stations folder: {stations_folder}")
        summary = get_stations_summary(stations_folder)
        print(f"Summary shape: {summary.shape}")
        replace_stations_summary_to_bank(summary, bank_path)
        print(f"Finished processing bank at {bank_path}")

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    # bank_path ="/groups/igonin/ecastillo/test/bank/RSNC"

    # stations_folder = os.path.join(bank_path,".stations")
    # df_summary = get_stations_summary(stations_folder)
    # # print(df_summary[["calculated","calculated_longitude",
    # #                 "calculated_latitude","calculated_num_entries"]])
    # # print(df_summary[["calculated","calculated_num_entries"]])
    # print(df_summary.describe())



    # replace_stations_summary_to_bank(df_summary, bank_path)

    # parent_folder = "/groups/igonin/ecastillo/test/bank"
    # replace_stations_to_multiple_banks(parent_folder)

    db_path = "/groups/igonin/ecastillo/UTDQuake/bank/uu/.index.db"
    # db_path = "/groups/igonin/ecastillo/test/bank/RSNC/.index.db"
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM '/stations/index'", conn,
                            parse_dates="creation_time")
    print(df)
    # print(df.describe())

    
    # parent_folder = "/groups/igonin/ecastillo/test/bank"
    # parent_folder = "/groups/igonin/ecastillo/UTDQuake/bank"
    # replace_stations_to_multiple_banks(parent_folder)
    
