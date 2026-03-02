import os

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/bck_utdq/test_021926"

from utdquake.utils.cache import list_local_networks
from obsplus import EventBank


banks = list_local_networks("bank")

# tx = EventBank(banks["uw"])
tx = EventBank(banks["RSNC"])

indices = tx.read_index()
ev_id = indices["event_id"].unique()[0:100]


cat = tx.get_events(event_id=ev_id)
print(cat)
cat.apply_utdq_qc(debug=True,inplace=True)

print(cat)