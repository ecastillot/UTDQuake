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
stats = scanner.get_stats(network="*",station="*",
                      location="*",instrument="[CH]H",
                      starttime=UTCDateTime("2024-08-01T00:00:00"), ##dates need to be previously calculated
                      endtime=UTCDateTime("2024-08-24T00:00:00"),
                    #   stats=["availability"]
                      )
print(stats.info())

min = 60
hour = 3600
day = 86400
colorbar = ut.StatsColorBar(stat="availability",
                            # cmap_name='Greens',
                            cmap_name='YlGn',
                            bad_colorname="red",
                            label_dict={"[0,20)":[0,20],
                                        r"[20,40)":[20,40],
                                        r"[40,60)":[40,60],
                                        r"[60,80)":[60,80],
                                        r"[80,100]":[80,100],
                                        # r"[80,99)":[80,99],
                                        # r"[99-100]":[99,100],
                                        }
                            )

plot_rolling_stats(stats=stats,freq="1h",major_step=4,
                       colorbar=colorbar,
                       major_format="%Y-%m-%d",
                       filter_stations=["PB17"],
                    #    starttime=datetime.datetime.strptime("2019-01-01 00:00:00", 
                    #                                         "%Y-%m-%d %H:%M:%S"),
                    #    endtime=datetime.datetime.strptime("2025-01-01 00:00:00", 
                    #                                         "%Y-%m-%d %H:%M:%S")
                       )

###########################

# colorbar = ut.StatsColorBar(stat="availability",
#                             label_dict={"No gaps":[0,1e-5],
#                                         r"$\leq 1$ hour":[1e-5,hour],
#                                         r"$\leq 12$ hours":[hour,hour*12],
#                                         r"$\leq 1$ day":[hour*12,day],
#                                         r"$\geq 1$ day":[day,day+0.1],
#                                         }
#                             )

# plot_rolling_stats(stats=stats,freq="1h",major_step=4,
#                        colorbar=colorbar,
#                        major_format="%Y-%m-%d",
#                     #    filter_stations=["PB17"],
#                     #    starttime=datetime.datetime.strptime("2019-01-01 00:00:00", 
#                     #                                         "%Y-%m-%d %H:%M:%S"),
#                     #    endtime=datetime.datetime.strptime("2025-01-01 00:00:00", 
#                     #                                         "%Y-%m-%d %H:%M:%S")
#                        )