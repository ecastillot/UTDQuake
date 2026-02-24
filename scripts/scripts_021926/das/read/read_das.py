# import obsplus
from obspy import read_events
import utdquake


path = "/groups/igonin/ecastillo/DAS_uw_data/GCI_QuakeML_Picks_01302026/11707158.qml"
catalog = read_events(path)

picks = catalog[0].picks_to_df()
arrivals = catalog[0].arrivals_to_df()
events = catalog.utdq_events_to_df()

picks.to_csv("/groups/igonin/ecastillo/utdquake/scripts/das/read/picks.csv", index=False)
arrivals.to_csv("/groups/igonin/ecastillo/utdquake/scripts/das/read/arrivals.csv", index=False)
events.to_csv("/groups/igonin/ecastillo/utdquake/scripts/das/read/events.csv", index=False)

# events= catalog.utdq_events_to_df()
# picks = catalog.utdq_picks_to_df()
# df = event.to_df()
# picks = event.picks

# print(events)
# print()
# print(catalog)