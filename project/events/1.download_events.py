import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import logging
import os
import pandas as pd
import obsplus
from obspy import UTCDateTime
from utdquake.bank.fdsn import Client
# from utdquake.bank import setup_logger

# logger = setup_logger(debug=False)
logger = logging.getLogger("download_events")
provider = "USGS"
# provider = "http://sismo.sgc.gov.co:8080/"
# provider = "BGR"
# provider = "http://sismo.sgc.gov.co:8080"
# provider = "http://eida"
bank_folder = "/groups/igonin/PHASED"

events_folder = os.path.join(bank_folder, "events")
stations_folder = os.path.join(bank_folder, "stations")
client =  Client(base_url=provider, 
            )
usgs_contributors = [ 'ci', 'se', 'tx',
                    'ismp', 'ak', 'nn', 'ld', 'pr', 'us', 
                    'uw', 'cgs', 'ew', 
                    'ok', 'admin', 'av', 'np', 'at',
                    'nm', 'mb', 
                    'uu', 'hv', 'pt', 'nc']


# client2 =  FDSNClient(provider)
starttime = UTCDateTime("2024-01-01T00:00:00")
endtime = UTCDateTime("2025-01-01T00:00:00")

# catalog = client.get_events(
#     starttime=starttime,
#     endtime=starttime + 7200,
#     # contributor="tx"
#     )
# print(catalog)
    # client.save_events_to_bank(
    #             base_path=events_folder,
    #             starttime=starttime,
    #             endtime=endtime,
    #             path_structure='{year}/{month}/{day}',
    #             name_structure='{event_id_end}',
    #             chunk_seconds=86400,
    #             max_n_events=20,
    #             calculate_d_az=True,
    #             stations_bank_path=stations_folder,
    #             workers = 16,
    #             contributor="tx"
    #         )

for contributor in usgs_contributors:
    logger.info(f"Downloading events for contributor: {contributor}")
    try:
        client.save_events_to_bank(
            base_path=events_folder,
            starttime=starttime,
            endtime=endtime,
            path_structure='{network}/{year}/{month}/{day}',
            name_structure='{event_id_end}',
            chunk_seconds=86400,
            max_n_events=100,
            calculate_d_az=True,
            stations_bank_path=stations_folder,
            workers = 16,
            contributor=contributor
        )
    except Exception as e:
        logger.error(f"Error downloading events for {contributor}")
