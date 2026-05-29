import os
# Set root
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
os.environ["UTDQUAKE_DAS_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

import logging
from utdquake.writers.parquet import build_manifests

logging.basicConfig(level=logging.INFO)

build_manifests(networks=["GCI"],
                das=True,
                # apply_utdqc=True,
                # include_events=True,
                # include_picks=True,
                # include_stations=True,
                include_networks=True,
                # force_put_picks=False,
                overwrite=True,
                )