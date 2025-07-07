import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import os
import pandas as pd
import obsplus
from obspy import UTCDateTime
from utdquake.bank.utils import append_inventory_to_catalog
from obspy.core.inventory import read_inventory
from obspy.clients.fdsn import Client


inv_path = "/groups/igonin/utdquake/bank/stations/TX.xml"
inventory = read_inventory(inv_path)

client = Client("USGS")
starttime = UTCDateTime("2024-01-01T00:00:00")
endtime = UTCDateTime("2024-01-03T00:00:00")
network = "tx"
cat = client.get_events(starttime=starttime, endtime=endtime, 
# contributor=network,
                        eventid="tx2024adok")

picks = cat.arrivals_to_df()
print(picks[["seed_id", "azimuth", "distance", "phase"]])
catalog, bad_inv_data = append_inventory_to_catalog(cat, inventory,debug=True)
print(catalog.events[0].preferred_origin().arrivals[0].__dict__)
print(catalog.events[0].preferred_origin().arrivals[-1].__dict__)
picks = cat.arrivals_to_df()
print(picks.info())
exit()
print(picks[["seed_id", "azimuth", "distance", "phase"]])

print(picks.columns.to_list())