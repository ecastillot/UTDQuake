from utdquake.bank.bank import UTDQBank
import obsplus
import pandas as pd
# bank = EventBank("/groups/igonin/ecastillo/UTDQuake/bank/ak")

path = "/home/edc240000/scratch/utdbank"
ebank = UTDQBank(base_path=path,
                path_structure='{year}/{month}/{day}',
                name_structure='{event_id_end}',
                format='quakeml')
stations_path = "/groups/igonin/ecastillo/DAS_uw_data/GCI_QuakeML_Picks_16042026/04012026/metadata/cable_metadata_04172026_utdq.csv"
stations_df = pd.read_csv(stations_path)
stations_df.dropna(inplace=True)
print(stations_df)
ebank.put_stations(stations_df,das=True)