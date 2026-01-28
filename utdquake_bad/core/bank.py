import os
import time
import sqlite3
import logging
from typing import List, Optional, Union
import pandas as pd
import obsplus
import matplotlib.pyplot as plt
from . import utils as fut

import datetime
from utdquake.core.path import get_manifest_path
from utdquake.utils.plot import (plot_overview,plot_stats,
                                 plot_station_location_uncertainty,
                                 plot_pick_histograms,
                                 plot_uncertainty_boxplots,
                                 plot_pick_stats,
                                 compute_region)

logger = logging.getLogger(__name__)

class EventBank(obsplus.EventBank):
    """
    EventBank extension for handling picks and station data.
    """

    def __init__(self, bank_path: str, *args, **kwargs) -> None:
        """
        Initialize EventBank.

        Args:
            bank_path (str): Path to the event bank.
        """
        super().__init__(bank_path, *args, **kwargs)
        self.manifest_picks_path = os.path.join(get_manifest_path(), "picks")
        self.contributor = os.path.basename(self.bank_path)
        self._sanitize()

    def _sanitize(self,events=True) -> None:
        """Perform sanity checks on the EventBank."""
        try:
            self.read_index()
        except Exception:
            logger.exception("Sanity check failed (index)")
            raise RuntimeError("EventBank sanity check failed (index)") from None
