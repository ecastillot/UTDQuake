import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_test"

from pathlib import Path
import utdquake as utdq
from utdquake.bank.bank import UTDQBank
import pandas as pd
from obspy import UTCDateTime

# fig_path = Path(__file__).parent / "utdq_density.png"
# print(f"Saving figure to {fig_path}")

bank_path = "/groups/igonin/ecastillo/UTDQuake_test/bank/GCI"
bank = UTDQBank(bank_path)

# print(bank)
# ev_id = bank.read_index()[["event_id"]].loc[0:10,"event_id"].to_list()

stations_path = "/groups/igonin/ecastillo/DAS_uw_data/GCI_QuakeML_Picks_16042026/04012026/metadata/cable_metadata_04172026_utdq.csv"
stations_df = pd.read_csv(stations_path)
stations_df.dropna(inplace=True)
print(stations_df)
bank.put_utdq_stations(stations_df,das=True,
            starttime=UTCDateTime("2023-11-09 04:43:30.917000"))