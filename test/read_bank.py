import os

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from utdquake.utils.cache import list_local_networks
import concurrent.futures as cf
from utdquake.core.obspy import EventBank
import logging

logging.basicConfig(level=logging.INFO)

banks = list_local_networks("bank")

tx = EventBank(banks["RSNC"])

stations = tx.get_stations()
print(stations)

