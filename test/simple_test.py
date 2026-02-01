import os 

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from pathlib import Path
import utdquake as utdq


# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

dataset = utdq.Dataset()
print(dataset)

# network level
network_data = dataset.networks
network_names = network_data["network"].tolist()

network = dataset.get_network(name=network_names[0])

# events
events = network.events
print(events)

# stations
stations = network.stations
print(stations)

# picks
picks = network.picks
print(picks)

# get event bank
ebank = network.bank # check obsplus.EventBank for more details
ev_ids = events["event_id"].iloc[:5].tolist()
cat = ebank.get_events(event_id=ev_ids)
print(cat)
cat2 = ebank.get_events(minmagnitude=4.3)
print(cat2)
