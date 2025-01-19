from obspy import UTCDateTime
from utdquake.clients.utd.client import Client

provider = "IRIS"
client =  Client(provider)

out = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events"
sta = client.get_custom_stations(output_folder=out,network="TX",station="PB*")
print(sta)
exit()


region = [-103.0,-94.5,33.5,37.5]
provider = "USGS"

# region = [-120.947,-112.740,31.721,37.353]
# provider = "https://service.scedc.caltech.edu/"
# provider = "USGS"

# region = [-104.84329,-103.79942,31.39610,31.91505] 
# provider = "USGS"

out = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events"

# provider = "IRIS"
client =  Client(provider)




# cat = client.get_events(starttime=UTCDateTime("2024-04-18T23:00:00"),
#                         endtime=UTCDateTime("2024-04-19T23:00:00"),
#                         minlatitude=region[2], maxlatitude=region[3], 
#                         minlongitude=region[0], maxlongitude=region[1],
#                         # includearrivals=True,
#                         # eventid="tx2024hrey"
#                         )
# print(cat[0].preferred_origin())
# # print(cat[0].eventid,cat[0].dataid)
# print(cat[0].picks)
# print(cat[0].preferred_origin().arrivals)
# exit()
cat,picks,mag = client.get_custom_events(starttime=UTCDateTime("2024-04-18T23:00:00"),
                        endtime=UTCDateTime("2024-04-19T23:00:00"),
                        minlatitude=region[2], maxlatitude=region[3], 
                        minlongitude=region[0], maxlongitude=region[1],
                        # includearrivals=True,
                        debug=True
                        # includepicks=True,
                        # output_folder=out,
                        #eventid="tx2024hstr",
                        #includeallmagnitudes=True,
                        )
# print(cat.info())
print(picks.info())
print(picks.describe())
# print(picks.describe())
# print(cat)
# print(picks)
# print(picks["polarity"].any())
# print(picks[picks[["polarity"]].notna().all(axis=1)]["polarity"])

# out = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/stats"
# provider = "TEXNET"
# client =  Client(provider)
# df = client.get_stats(
#     network="TX",station="PB16",
#     location="00",channel="HH*",
#     starttime=UTCDateTime("2024-04-18T23:00:00"),
#     endtime=UTCDateTime("2024-04-19T23:00:00"),
#     output=out,
#     step=3600)

# print(df)



# print(cat[0].info())
# print(cat[0]["loc_method_id"])
# print(cat[0]["earth_model_id"])
# print(cat[0]["associated_phase_count"])
# print(cat[0]["used_phase_count"])

# x = cat[1]
# print(x[x["ev_id"].isin(["texnet2024hrey"])])
    