import os
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

import sys
sys.path.insert(0, "/groups/igonin/ecastillo/bck_utdq/UTDQuake")

from utdquake_dld.core.manifest import build_manifests

import logging
import pandas as pd

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# # manual_info_path = "/groups/igonin/ecastillo/utdquake/data/others/manual_info.csv"
# # manual_info = pd.read_csv(manual_info_path)
paths = build_manifests(
    force_download=False,
    overwrite=True,
    include_events = False,
    include_stations = True,
    include_picks = False,
    include_stats = False,
    per_network_shards=True,  # BEST for big datasets
    # networks=["RSNC"],
    # include_manual_network_info=manual_info

)
# print(paths.manifest_dir)


# from pathlib import Path
# import pandas as pd

# Replace with your e
# df_events = pd.read_parquet(events_manifest)  # or pd.read_csv(events_manifest)
# print(df_events.head())
# # print(df_events["network"].value_counts())
# # print(df_events.info())
# # print(df_events["origin_id"])