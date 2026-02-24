import os

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/bck_utdq/test_021926"

from utdquake.utils.cache import list_local_networks
from obsplus import EventBank
# from utdquake.patch.qc import PICK_QC_DEFAULTS, EVENT_QC_DEFAULTS
# from utdquake.core.parquet import PREF_PICKS_TYPES, sanitize_dataframe_for_parquet



banks = list_local_networks("bank")

# tx = EventBank(banks["uw"])
tx = EventBank(banks["uw"])

picks = tx.picks
t = picks.query(
    'resource_id_arrival in ["quakeml:uw.anss.org/AssocArO/UW/17409843", '
    '"quakeml:uw.anss.org/AssocArO/UW/17409848"]'
)
print(t)

exit()

indices = tx.read_index()
ev_id = indices["event_id"].unique()[0:100]
# print(ev_id )
cat = tx.get_events(event_id=ev_id)
print(cat)
# PICK_QC_DEFAULTS["sp_threshold"] = {("S", "P"): (20, 100)}
cat.apply_utdq_qc(debug=True,inplace=True)
print(cat)

events = cat.utdq_events_to_df()
print(events.info())
events = sanitize_dataframe_for_parquet(events)
print(events.info())

picks = cat.utdq_picks_to_df()
print(picks.info())
picks = sanitize_dataframe_for_parquet(picks)
print(picks.info())

exit()

# ##### test
# events = events[events["p_phase_count"] < 4]
# events_ids = events["event_id"].unique()
# print(events_ids)

# new_cat = tx.get_events(event_id=events_ids)
# picks = new_cat.utdq_picks_to_df()
# print(picks)
# ##### test

events = events_qc(events, min_associated_phase_count=4,
                    min_used_phase_count=4,
                    min_station_count=3,
                    max_standard_error=1.8,
                    debug=True)

cat = apply_events_qc_to_catalog(cat, events, debug=True)

print(cat)
# print(cat.utdq_events_to_df().info())
exit()

picks_df = cat.utdq_picks_to_df()
print(f"before qc {len(picks_df)} picks")
picks_df_qc = picks_qc(picks_df, debug=False,
                       sp_threshold={("S", "P"): (20, 100)}
)

cat_qc = apply_picks_qc_to_catalog(cat, picks_df_qc, debug=True)
picks_df = cat.utdq_picks_to_df()
print(cat_qc)
print(f"after qc {len(picks_df)} picks")



# print(picks[picks["hyp_distance"]<0])
# print(picks[picks["hyp_distance"].isna()])

# print(f"before qc {len(picks)}")
# print(f"after qc {len(picks)}")

# print(cat.to_df())
# print(cat.arrivals_to_df())
# print(cat.utdq_picks_to_df()[["travel_time","hyp_distance"]])
# print(cat.utdq_picks_to_df().info())
# print(cat.utdq_picks_to_df()[["evaluation_mode"]])
# print(cat.events)






# pick_nets = list_local_networks("picks")
# event_nets = list_local_networks("events")



# print(network)
# print(pick_nets)
# print(event_nets)

# ok, I have an idea, but first help me to create a qc step, 
# I have the dataframes with the arrivals that I want to remove 
