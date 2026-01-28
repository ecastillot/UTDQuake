from utdquake.fdsn.client import Client
from obspy import UTCDateTime

tx = "USGS"
client = Client(tx)
starttime = UTCDateTime("2020-01-27T00:00:00")
endtime = UTCDateTime("2020-01-27T00:10:00")
check_picks = client.check_picks(
                        starttime=starttime,
                        endtime=endtime, 
                        chunk_seconds=120,
                        patience=5)

print(check_picks)
