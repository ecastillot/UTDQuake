import os
# Set root
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

import logging
from utdquake.writers.parquet import build_manifests

logging.basicConfig(level=logging.INFO)

build_manifests(networks=["tx"],
                apply_utdqc=True,
                include_events=True,
                # force_put_picks=False,
                overwrite=True,
                )