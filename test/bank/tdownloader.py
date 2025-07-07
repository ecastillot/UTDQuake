import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import os
import pandas as pd
import obsplus
from obspy import UTCDateTime
from utdquake.bank.fdsn import Client
from utdquake.bank import setup_logger

logger = setup_logger(debug=False)

provider = "USGS"
# provider = "http://sismo.sgc.gov.co:8080/"
# provider = "BGR"
# provider = "http://sismo.sgc.gov.co:8080"
# provider = "http://eida"
bank_folder = "/groups/igonin/utdquake/bank"
events_folder = os.path.join(bank_folder, "events")
stations_folder = os.path.join(bank_folder, "stations")
bank =  Client(provider)
starttime = UTCDateTime("2024-01-01T00:00:00")
endtime = UTCDateTime("2024-01-03T00:00:00")

# bank.save_stations_to_bank(
#     base_path=stations_folder)

bank.save_events_to_bank(
    base_path=events_folder,
    starttime=starttime,
    endtime=endtime,
    chunk_seconds=7200,
    max_n_events=200,
    calculate_d_az=True,
    stations_bank_path=stations_folder,
    workers = 16,
    debug=True
    # contributor="ak"
    # minlatitude=region[2], maxlatitude=region[3],
    # minlongitude=region[0], maxlongitude=region[1],
)

# bank.save_events_to_bank(
#     base_path=events_folder,
#     starttime=starttime,
#     endtime=endtime,
#     max_n_events=254,
#     # contributor="ak"
#     # minlatitude=region[2], maxlatitude=region[3],
#     # minlongitude=region[0], maxlongitude=region[1],
# )


# ebank = obsplus.EventBank(base_path=events_folder)
# print(ebank)
# print(ebank.path_structure)
# print(ebank.name_structure)
# print(ebank.get_event_summary())

# event_sumary = ebank.get_event_summary()
# event_sumary.to_csv("/groups/igonin/ecastillo/UTDQuake/test/bank/test_event_summary.csv", index=False)
# df_index = ebank.read_index()
# _df_index = df_index[(df_index.time >= pd.Timestamp('2024-01-28T00:00:00')) & (df_index.time <= pd.Timestamp('2024-01-29T00:00:00'))]
# cat_pre = ebank.get_events(event_id=_df_index.event_id.values)

# print(cat_pre)