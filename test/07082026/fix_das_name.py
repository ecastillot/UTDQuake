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

old_folder = Path("/groups/igonin/ecastillo/UTDQuake_DAS")
new_folder = Path("/groups/igonin/ecastillo/UTDQuake_DAS_new")
previous_name = "GCI"
new_name = "UWF"
mode = "network_DAS"

raw_folder = old_folder / mode
new_folder = new_folder / mode

if mode == "events_DAS":
    args_type = PREF_EVENTS_TYPES
    args_order = PREF_EVENTS_ORDER
elif mode == "picks_DAS":
    args_type = PREF_PICKS_TYPES
    args_order = PREF_PICKS_ORDER
elif mode == "network_DAS":
    args_type = PREF_NETWORK_TYPES
    args_order = PREF_NETWORK_ORDER
elif mode == "stations_DAS":
    args_type = PREF_STATIONS_TYPES
    args_order = PREF_STATIONS_ORDER
else:
    raise ValueError(f"Unknown mode: {mode}")

print(raw_folder)

if mode == "network_DAS":
    previous_name = "network.parquet"
else:
    previous_name = f"network={previous_name}.parquet"

for path in raw_folder.glob(previous_name):

    if mode == "network_DAS":
        new_path = new_folder / f"network.parquet"
    else:
        new_path = new_folder / f"network={new_name}.parquet"

    print(f"Processing {path} -> {new_path}")

    df = pd.read_parquet(path)
    df = sanitize_dataframe(df)
    df["network"] = new_name

    df = sanitize_dataframe(df,
                            string_cols=args_type["string_cols"],
                            float_cols=args_type["float_cols"],
                            int_cols=args_type["int_cols"],
                            datetime_cols=args_type["datetime_cols"],
                            bool_cols=args_type["bool_cols"],
                            order_cols=args_order)

    new_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(new_path, index=False)
