import utdquake
import obsplus
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
from pathlib import Path
# from utils import catalog_generator
import os
import numpy as np
import datetime as dt
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# PROVIDER = "http://eida-federator.ethz.ch"
# PROVIDER = "http://www.isc.ac.uk"
# PROVIDER = "IRIS"
# PROVIDER = "http://earthquake.usgs.gov"
# PROVIDER = "USGS"
PROVIDER = "https://service.earthscope.org"

bank_path = Path("/groups/igonin/ecastillo/UTDQuake_ak/bank/ak")
path_structure='{year}/{month}/{day}'
name_structure='{event_id_end}'
ebank = obsplus.EventBank(
                base_path=bank_path,
                path_structure=path_structure,
                name_structure=name_structure,
            )

path = "/groups/igonin/ecastillo/utdquake/scripts2/das_fig/ak_network/0.das_events.csv"
df = pd.read_csv(path)
# print(df[["time","event_id"]])

client = Client(PROVIDER)

catalog = client.get_events(
    contributor="ak", 
starttime=UTCDateTime("2024-09-07 20:17:46"), 
endtime=UTCDateTime("2024-09-07 20:17:47"), 
# eventid="query?eventid=11882157",
# # eventid="11882157",
# eventid="024bjfwitn",
# includearrivals=True
)
print(catalog[0])
print(catalog[0].picks)
event = catalog[0]
origin = event.preferred_origin() or event.origins[0]

# print(event.resource_id.id.split("/")[-1])
# print(event.creation_info.agency_id + event.resource_id.id.split("/")[-1])
# print(event.extra.datasource.value + event.extra.eventid.value)
# print(event.extra.eventid.value)
# print(event.extra.datasource.value)

print(origin.arrivals)

# for i, row in df.iterrows():
#     event_id = row["event_id"]
#     event_id = event_id.split("=")[-1]
#     # print(event_id)

#     print(f"-->{i}/{len(df)}, Event: {event_id}")
#     catalog = client.get_events(eventid=str(event_id),
#                                 contributor="ak",
#                                 includearrivals=True,
#                                 orderby="time")
#     print(catalog[0].picks)
    # print(catalog.utdq_picks_to_df())
    # print
    # try:
    #     ebank.put_events(catalog)
    # except Exception as e:
    #     print(f"Error printing catalog: {e}")


    

# path_structure='{year}/{month}/{day}'
# name_structure='{event_id_end}'
# events_bank_path = data_dir/"events"/"bank"
# os.makedirs(events_bank_path, exist_ok=True)
# # for data in cat_gen:
#     cat, start, end = data["catalog"], data["starttime"], data["endtime"]
#     print(f"-->Start: {start}, End: {end}, Events in catalog: {len(cat)}")
    # try:
    #     ebank.put_events(cat)
    # except Exception as e:
    #     print(f"Error printing catalog: {e}")

# events = client.get_events(network=networks,starttime=starttime, endtime=endtime)

# events = events.to_df()
# print(events)
# events.to_csv(data_dir/"events.csv",index=False)