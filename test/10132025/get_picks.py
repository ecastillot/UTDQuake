import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

from utdquake.bank.event_bank import EventBank
from utdquake.bank.utils import merge_arrivals_and_picks

path = "/groups/igonin/ecastillo/UTDQuake/project_25092025/events/TestBank/events/tx"
# picks_path = "/groups/igonin/ecastillo/UTDQuake/17092025/picks.csv"

ebank = EventBank(
        base_path=path,
        path_structure='{year}/{month}/{day}/{hour}',
        name_structure='{event_id_end}',
        format='quakeml'
    )
# events = ebank.read_index()
# cat = ebank.get_events(event_id=events.event_id.values)
# cat = ebank.get_events(event_id=events.iloc[0:30].event_id.values)
print(ebank.get_table_names())
# picks = cat.picks_to_df()
# arrivals = cat.arrivals_to_df()
# picks = merge_arrivals_and_picks(arrivals, picks)



# picks.to_csv(picks_path, index=False)
# # print(picks.info())
# print(events.info())