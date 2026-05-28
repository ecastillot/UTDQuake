# import obsplus
from obspy import read_events
import utdquake


path = "/groups/igonin/ecastillo/DAS_uw_data/GCI_QuakeML_Picks_16042026/04012026/11707158.qml"
catalog = read_events(path)

print(catalog)
 
event = catalog[0]
origin = event.preferred_origin() or event.origins[0]

# Convert phases to uppercase
for arr in origin.arrivals:
    arr.phase = arr.phase.upper()  # "p" -> "P", "s" -> "S"


picks = catalog[0].picks_to_df()
arrivals = catalog[0].arrivals_to_df()
events = catalog.utdq_events_to_df()

picks.to_csv("/groups/igonin/ecastillo/utdquake/scripts/das/test_alex/picks.csv", index=False)
arrivals.to_csv("/groups/igonin/ecastillo/utdquake/scripts/das/test_alex/arrivals.csv", index=False)
events.to_csv("/groups/igonin/ecastillo/utdquake/scripts/das/test_alex/events.csv", index=False)

# # events= catalog.utdq_events_to_df()
# # picks = catalog.utdq_picks_to_df()
# # df = event.to_df()
# # picks = event.picks

# print(events)
# print()
# print(catalog)