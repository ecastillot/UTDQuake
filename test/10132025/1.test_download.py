import logging
import os
import pandas as pd
import obsplus
from obspy import UTCDateTime
from utdquake.download.fdsn import Client

bank_folder = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test"
stations_folder = "/groups/igonin/ecastillo/Bank/stations"
availability_path = "/groups/igonin/ecastillo/UTDQuake/test/bank/info.csv"


logger = logging.getLogger("download_events")

starttime = UTCDateTime("2010-01-01T00:00:00")
endtime = UTCDateTime("2025-08-01T00:00:00")


events_folder = os.path.join(bank_folder, "tx")
agency = "TX"
provider = "USGS"
contributor = "tx"
client =  Client(base_url=provider)

client.download_events(
            events_bank_path=events_folder,
            starttime=starttime,
            endtime=endtime,
            path_structure='{year}/{month}/{day}',
            name_structure='{event_id_end}',
            patience=100,
            chunk_seconds=86400,
            max_n_events=5000,
            max_from_bank=True,
            calculate_d_az=True,
            stations_bank_path=stations_folder,
            reverse=True,
            workers = 50,
            contributor=contributor 
        )