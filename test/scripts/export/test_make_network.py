import os
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/bck_utdq/test_021926"

import logging
from utdquake.dataset.writers.parquet import build_manifests

logging.basicConfig(level=logging.INFO)
build_manifests()

