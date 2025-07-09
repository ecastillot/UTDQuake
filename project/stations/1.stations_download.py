import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import os
import pandas as pd
from obspy import UTCDateTime
from obspy.clients.fdsn.header import URL_MAPPINGS
from utdquake.bank.fdsn import Client

report_path = "/groups/igonin/ecastillo/UTDQuake/project/stations/stations_report.csv"
bank_folder = "/groups/igonin/PHASED"
report = pd.read_csv(report_path)
report = report[report["station"] == True]
print(report)
stations_folder = os.path.join(bank_folder, "stations")


for index,row in report.iterrows():
    agency = row["agency"]
    url = row["url"]

    if agency in ["IRIS","IRISPH5","AUSPASS","BGR","EIDA"]:
        continue  # Skip IRIS as it is handled separately

    print(f"Agency: {agency}, URL: {url} [{index+1}/{len(report)}]")
    client =  Client(url)

    client.save_stations_to_bank(
        base_path=stations_folder,
        workers=10)


# provider = "IRIS"
# provider = "http://eida.ethz.ch"
# provider = "http://eida.ethz.ch"
# provider = "http://eida.ethz.ch"
# provider = "texnet"
# provider = "http://sismo.sgc.gov.co:8080"
# provider = "USGS"
# client =  Client(provider)

# client.save_stations_to_bank(
#     base_path=stations_folder,
#     workers=10)