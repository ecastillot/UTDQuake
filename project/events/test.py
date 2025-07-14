import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)


import glob
import os
import obsplus
from obspy import read_events
from utdquake.bank.event_bank import EventBank
# Example usage
# test_path = "/groups/igonin/Bank/events/uu"
# xml_files = glob.glob(os.path.join(test_path, "**","*.xml"),recursive=True)
# len_xml_files = len(xml_files)
# print(f"Found {len_xml_files} XML files in {test_path}")

# cat = read_events("/groups/igonin/Bank/events/tx/2024/01/01/texnet2024aaaa.xml")
# df = cat.to_df()
# arrivals = cat.arrivals_to_df()
# picks = cat.picks_to_df()
# print(arrivals)
# print(picks)
# # print(df.info())
# # print(df[["event_id"]].head())

path = "/groups/igonin/Bank/events/tx"
ebank = EventBank(
        base_path=path,
        path_structure='{year}/{month}/{day}/{hour}',
        name_structure='{event_id_end}',
        format='quakeml'
    )
# events = ebank.get_event_summary()
# print(events)
# stations = ebank.get_station_summary(available=False)
# print(stations)

summary = ebank.get_summary()
specific_summary = summary.iloc[:,4::]
print(specific_summary.sum(axis=0).to_dict())
