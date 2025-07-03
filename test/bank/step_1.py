import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

from obspy.clients.fdsn.header import URL_MAPPINGS
import os
import pandas as pd
from utdquake.bank.fdsn import (Client,catalog_generator,
                    extend_fdsn_url_mappings, generate_agency_availability_report,
                    plot_agencies_stations)
from obspy import UTCDateTime

output = "/groups/igonin/ecastillo/UTDQuake/test/bank/info.csv"
png_output = "/groups/igonin/ecastillo/UTDQuake/test/bank/info.png"
df = pd.read_csv(output)

plot_agencies_stations(df,png_output,debug=True)


exit()

## Parameters
starttime = UTCDateTime("2024-01-01T00:00:00")
endtime = UTCDateTime("2024-12-02T00:00:00")
chunk_seconds=3600
patience=10
debug = True
output = "/groups/igonin/ecastillo/UTDQuake/test/bank/info.csv"
additional_mappings = {}

#code
df = generate_agency_availability_report(
                                    starttime=starttime,
                                    endtime=endtime,
                                    chunk_seconds=chunk_seconds,
                                    patience=patience,
                                    output=output,
                                    debug=debug,
                                    additional_mappings=additional_mappings
                                )
print(df)

exit()
        # print(f"\t",services)
# provider  = "IRIS"
# provider  = "NCEDC"
# provider  = "SCEDC"
# provider = "http://eida.ethz.ch"
# provider = "USGS"
provider = "ICGC"
client = Client(provider )
# catalog = client.get_events(starttime=UTCDateTime("2024-01-01T00:00:00"),
#                           endtime=UTCDateTime("2024-01-02T00:00:00"),
#                           eventid=40453703
#                         #   includearrivals=True
#                           )
# print(client.__dict__)
# services = client.get_available_services()
# print(f"\t",services)
# print(catalog)
# print(catalog[0])

# info = client.get_available_picks( starttime=UTCDateTime("2024-01-01T00:00:00"),
#                             endtime=UTCDateTime("2024-01-02T00:00:00"))
                            # endtime=UTCDateTime("2024-12-02T00:00:00"))
# print(info)
# generator = catalog_generator(client=client,
#         starttime=UTCDateTime("2024-01-01T00:00:00"),
#         endtime=UTCDateTime("2024-01-02T00:00:00"),
#         chunk_seconds=3600,
#         debug=True)
# print(generator)
# origin_time = None
# for i, catalog in enumerate(generator):
#     if i >= patience:
#         break  # Stop after N iterations if no event is found
#     if len(catalog) > 0:
#         event = catalog[0]
#         origin_time = event.preferred_origin().time
#         break
# print(origin_time)
    