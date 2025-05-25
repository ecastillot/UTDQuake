import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import os
from obspy import UTCDateTime
from utdquake.bank.fdsn import Bank

region = [-104.84329,-103.79942,31.39610,31.91505]
provider = "IRIS"
# provider = "USGS"
bank_folder = "/groups/igonin/utdquake/bank"
stations_folder = os.path.join(bank_folder, "stations")
bank =  Bank(provider)
bank.save_stations(
    base_path=stations_folder,
    # workers= None,
    # level="channel",
    # minlatitude=region[2], maxlatitude=region[3],
    # minlongitude=region[0], maxlongitude=region[1],
)


# client.save_events(
#     base_path=out,
#     starttime=UTCDateTime("2024-04-18T23:00:00"),
#     endtime=UTCDateTime("2024-04-19T23:00:00"),
#     minlatitude=region[2], maxlatitude=region[3],
#     minlongitude=region[0], maxlongitude=region[1])