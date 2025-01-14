from obspy import UTCDateTime
from utdquake.clients.utd.client import Client

provider = "USGS"
client =  Client(provider)
region = [-104.84329,-103.79942,31.39610,31.91505]
out = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events"
cat,picks,mag = client.get_custom_events(starttime=UTCDateTime("2024-04-18T23:00:00"),
                        endtime=UTCDateTime("2024-04-19T23:00:00"),
                        minlatitude=region[2], maxlatitude=region[3], 
                        minlongitude=region[0], maxlongitude=region[1],
                        includeallorigins=True,
                        # output_folder=out,
                        #eventid="tx2024hstr",
                        #includeallmagnitudes=True,
                        )
print(cat.info())
print(picks.info())

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
    