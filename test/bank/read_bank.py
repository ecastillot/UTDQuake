import obsplus
import os


bank_folder = "/groups/igonin/utdquake/bank"
events_folder = os.path.join(bank_folder, "events")
ebank = obsplus.EventBank(base_path=events_folder,
                          path_structure='{year}/{month}/{day}/{hour}',
                          name_structure='{event_id_end}',
                          format='quakeml')
print(ebank)
df_index = ebank.read_index()
print(df_index)