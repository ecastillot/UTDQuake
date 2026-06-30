import pandas as pd
from pathlib import Path
from utdquake.writers.schema import (
            PREF_PICKS_ORDER,
            PREF_PICKS_TYPES,
            PREF_EVENTS_ORDER,
            PREF_EVENTS_TYPES,
            PREF_NETWORK_ORDER,
            PREF_NETWORK_TYPES,
            PREF_STATIONS_ORDER,
            PREF_STATIONS_TYPES,
            sanitize_dataframe)

raw_folder = Path("/groups/igonin/ecastillo/UTDQuake/events")
new_folder = Path("/groups/igonin/ecastillo/UTDQuake_new/events")

for path in raw_folder.glob("network=*.parquet"):
    new_path = new_folder / path.name
    # name = path.name
    network_name = path.name.split("=")[-1].split(".")[0]
    print(path,new_path,network_name)

    df = pd.read_parquet(path)
    df = sanitize_dataframe(df)
    df["network"] = network_name

    df = sanitize_dataframe(df,
                            string_cols=PREF_EVENTS_TYPES["string_cols"],
                            float_cols=PREF_EVENTS_TYPES["float_cols"],
                            int_cols=PREF_EVENTS_TYPES["int_cols"],
                            datetime_cols=PREF_EVENTS_TYPES["datetime_cols"],
                            bool_cols=PREF_EVENTS_TYPES["bool_cols"],
                            order_cols=PREF_EVENTS_ORDER)

    new_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(new_path, index=False)
