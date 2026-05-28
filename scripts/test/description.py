import os
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/bck_utdq/test_021926"

import utdquake as utdq
from utdquake.core.obspy import EventBank
from utdquake.utils.cache import list_local_networks
from utdquake.utils.utils import get_network_summary

dataset = utdq.Dataset()
network_data = dataset.networks
network = dataset.get_network(name="RSNC")

stations = network.stations
events = network.events
t = get_network_summary(stations, events)

print(t)