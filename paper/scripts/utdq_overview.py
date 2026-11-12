import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import _local  # noqa: F401  (local root of the version, PAPER_VERSION; figures in paper/<version>/)

import utdquake as utdq

# world maps of the version: earthquakes above stations (paper), and side by side with the 5 statistics
# panels (docs, versions page). Station counts are distinct (network, station) pairs.
dataset = utdq.Dataset()
print(dataset.description)
title = {"v1": "UTDQuake v1.0", "v2": "UTDQuake v2"}[_local.VERSION]
n = len(dataset.networks)
dataset.plot_global_overview(layout="vertical", title=f"{title}: {n} networks",
                             savepath=_local.OUT / "utdq_overview.png")
dataset.plot_global_overview(layout="combined", title=f"{title}: {n} networks",
                             savepath=_local.OUT / "utdq_overview_stats.png")
