import os
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
from utdquake.core.manifest import build_manifests

import logging
import pandas as pd
logger = logging.getLogger(__name__)

manual_info_path = "/groups/igonin/ecastillo/utdquake/utdquake/core/manual_info.csv"
manual_info = pd.read_csv(manual_info_path)
paths = build_manifests(
    force_download=False,
    overwrite=True,
    include_events = True,
    include_stations = True,
    include_picks = True,
    include_stats = True,
    per_network_shards=True,  # BEST for big datasets
    # networks=["RSNC"],
    include_manual_network_info=manual_info

)
print(paths.manifest_dir)


# from pathlib import Path
# import pandas as pd

# # Replace with your actual paths
# root = Path("/groups/igonin/ecastillo/UTDQuake")
# events_manifest = root / "manifests" / "picks/network=ak.parquet"  # or events.csv

# df_events = pd.read_parquet(events_manifest)  # or pd.read_csv(events_manifest)
# print(df_events.head())
# print(df_events["network"].value_counts())
# print(df_events.info())
# print(df_events["origin_id"])