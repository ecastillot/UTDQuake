from obspy import UTCDateTime
from obspy.clients.fdsn import Client

from utdquake.scan.scanner import *
import matplotlib.colors as mcolors

starttime = UTCDateTime("2024-08-01T00:00:00")
endtime = UTCDateTime("2024-08-24T00:00:00")

# starttime = UTCDateTime("2024-01-01T00:00:00")
# endtime = UTCDateTime("2024-08-01T00:00:00")
wav_restrictions = WaveformRestrictions(
            "TX,2T,4T,4O",
            "*",
            "*","*",
            starttime,endtime,
            location_preferences=["", "00", "20", "10", "40"],
            instrument_preferences=["HH","","BH", "EH", "HN", "HL"],
            remove_networks=[], 
            remove_stations=[],
        #   filter_domain=[-104.6,-104.4,31.6,31.8], #lonw,lone,lats,latn #subregion
        #   filter_domain=[-104.5,-103.5,31,32], #lonw,lone,lats,latn #big region
        #   filter_domain=[-105,-103.5,31,32], #lonw,lone,lats,latn #AOI1
            filter_domain=[-104.84329,-103.79942,31.39610,31.91505], #lonw,lone,lats,latn #AOI2
            
            )   
client= Client("TEXNET")
provider = Provider(client=client,
                    wav_restrictions=wav_restrictions)
db_path = "/home/emmanuel/ecastillo/dev/utdquake/test/scan/tx"
scanner = Scanner(db_path,providers=[provider],configure_logging=True)
scanner.scan(step=3600,wav_length=86400,level="station",n_processor=4)