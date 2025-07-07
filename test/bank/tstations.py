import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import os
from obspy import UTCDateTime
from obspy.clients.fdsn.header import URL_MAPPINGS
from utdquake.bank.fdsn import Client

region = [-104.84329,-103.79942,31.39610,31.91505]
# provider = "IRIS"
# provider = "http://eida.ethz.ch"
provider = "http://eida.ethz.ch"
# provider = "http://eida.ethz.ch"
# provider = "USGS"
bank_folder = "/groups/igonin/utdquake/bank2"
stations_folder = os.path.join(bank_folder, "stations")
client =  Client(provider)

client.save_stations_to_bank(
    base_path=stations_folder,
    workers=10)

# print(client.__dict__)
# print(client.services["available_event_contributors"])
# print(client._picks_availability())
# print(client._picks_in_eventid_mode())

# print(list(client.services.keys()))
# print(cli)
# print(client.help(service="event"))

# print(client.available_event_contributors)
# exit()
# services = client.get_available_services()
# print(services)

# ev_ids = client._get_custom_event_ids(starttime=UTCDateTime("2024-04-18T23:00:00"),
#                              endtime=UTCDateTime("2024-04-19T23:00:00"),)
# print(ev_ids)


# tests = {"f1":lambda x: x["resource_id"]["id"]}
# # tests = {"f1":lambda x: x.resource_id.id}

# eit = EventIDTester({"resource_id":{"id":"hola"}},tests=tests)
# id = eit.get_event_id("f1")
# print(id)
# print("natural mode",client._picks_in_natural_mode())
# print("eventid mode",client._picks_in_eventid_mode())
# services = client.get_available_services()
# print(services)
# services = client.services
# for key,val in services["event"].items():
#     print(f"{key}: {val}")

# print(services["event"]["include_arrivals"])
# print(list(services.keys()))
# print(list(services.values()))
# for provider in URL_MAPPINGS:
#     print(provider, ":", URL_MAPPINGS[provider])
# services = get_available_fdsn_services(provider)
# print(services)

# services = get_available_services(bank)
# print(services)



# bank.save_stations(
#     base_path=stations_folder,
#     # workers= None,
#     # level="channel",
#     # minlatitude=region[2], maxlatitude=region[3],
#     # minlongitude=region[0], maxlongitude=region[1],
# )


# client.save_events(
#     base_path=out,
#     starttime=UTCDateTime("2024-04-18T23:00:00"),
#     endtime=UTCDateTime("2024-04-19T23:00:00"),
#     minlatitude=region[2], maxlatitude=region[3],
#     minlongitude=region[0], maxlongitude=region[1])