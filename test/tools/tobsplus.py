import sys
lib = None
lib = "/home/edc240000/UTDQuake"
if lib is not None:
    sys.path.append(lib)


from obspy import UTCDateTime
from utdquake.clients.fdsn.client import Client
import obsplus
import pandas as pd
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees
from obspy.clients.fdsn import Client
from scipy.spatial import KDTree

region = [-104.84329,-103.79942,31.39610,31.91505]
provider = "USGS"
out = "/home/edc240000/UTDQuake/test/tools/custom_events"


# client =  Client(provider)
# # cat = client.get_events(starttime=UTCDateTime("2024-04-18T23:00:00"),
# #                         endtime=UTCDateTime("2024-04-19T23:00:00"),
# #                         minlatitude=region[2], maxlatitude=region[3],
# #                         minlongitude=region[0], maxlongitude=region[1],
# #                         # includeallorigins =True,
#                         # includeallmagnitudes=True,
# #                         includearrivals=True,
# #                         )

# custom_events = client.get_chunked_events(starttime=UTCDateTime("2024-04-18T23:00:00"),
#                         endtime=UTCDateTime("2024-04-19T23:00:00"),
#                         base_path=out,
#                         minlatitude=region[2], maxlatitude=region[3],
#                         minlongitude=region[0], maxlongitude=region[1],
#                         includearrivals=True,
#                         debug=False,
#                         workers=None
#                         # output_folder=out,
#                         )



# Re-initialize connection to the EventBank
ebank = obsplus.EventBank(base_path=out)
print(ebank)
# Note that the `path_structure` or `name_structure` key-word arguments we defined are saved!
print('Our Event Bank values')
print(ebank.path_structure)
print(ebank.name_structure)
print('Default values')
print('{year}/{month}/{day}')
print('{time}_{event_id_short}')

df_index = ebank.read_index()
# Subset by origin times
_df_index = df_index[(df_index.time >= pd.Timestamp('2024-04-19T09:00:00')) & (df_index.time <= pd.Timestamp('2024-04-19T23:00:00'))]
# Get events from your event bank
cat_pre = ebank.get_events(event_id=_df_index.event_id.values)
cat = cat_pre.copy()
print(cat)
print(cat.picks_to_df())

# # Run small corrections
# for event in cat.events:
#     for pick in event.picks:
#         sn = pick.waveform_id.station_code
#         print(pick.waveform_id)
#         pick.waveform_id.station_code=sn.split('.')[0]
#         pick.waveform_id.network_code=sn.split('.')[1]
df_picks = cat.arrivals_to_df()
# print(df_picks)

# client =  Client(provider)
client = Client('IRIS')
nets = ','.join(list(df_picks.network.unique()))
stas = ','.join(list(df_picks.station.unique()))
print(nets)
print(stas)
inv = client.get_stations(network=nets, station=stas, level='channel')
df_stations =inv.to_df()
print(df_stations)


origin_gaps = []
for event in cat.events:
    # Iterate across origins
    for origin in event.origins:
        olon = origin.longitude
        olat = origin.latitude
        # Iterate across associated arrivals
        bazs = set([])
        for arrival in origin.arrivals:
            # Get pick observations
            pick = arrival.pick_id.get_referred_object()
            # Get station location
            network = pick.waveform_id.network_code
            station = pick.waveform_id.station_code
            print(network,station)
            _df_sta = df_stations[(df_stations.network==network) & (df_stations.station==station)][['station','network','latitude','longitude']]
            try:
                slon = _df_sta.longitude.values[0]
                slat = _df_sta.latitude.values[0]
            except:
                continue
            # Get distances
            dist_m, seaz, esaz = gps2dist_azimuth(slat, slon, olat, olon)
            print(arrival.distance,arrival.azimuth)
            # Convert distance to degrees
            arrival.distance = kilometer2degrees(dist_m*1e-3)
            # Assign back-azimuth
            arrival.azimuth = esaz
            print(arrival.distance,arrival.azimuth)
            
## A task for the HACK-A-THON, get azimuthal gaps into your EventBank

            bazs.add(esaz)

        
        # Calculate gaps
        bazs = list(bazs)
        bazs.sort()
        gaps = [bazs[_e+1] - bazs[_e] for _e in range(len(bazs)-1)] + [360 - bazs[-1] + bazs[0]]
        # Get maximum azimuthal gap
        maxgap = max(gaps)
        # associate with resourceID
        origin_gaps.append([origin.resource_id.id, maxgap])

# An exercise for users to incorporate 'gap' values into their preferred schema
print(pd.DataFrame(origin_gaps, columns=['resource_id','gap']))

for event in cat.events:
    preferred_origin = event.preferred_origin()
    origin_quality = preferred_origin.quality
    print(origin_quality)