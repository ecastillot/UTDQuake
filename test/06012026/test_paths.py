import os
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
# os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
# os.environ["UTDQUAKE_DAS_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

from pathlib import Path
import utdquake as utdq
from utdquake.bank.bank import UTDQBank
from utdquake.core.config import get_utdq_paths
from utdquake.core.load import resolve_network_paths
from utdquake.bank.bank import UTDQBank
# fig_path = Path(__file__).parent / "utdq_density.png"
# print(f"Saving figure to {fig_path}")
import logging

logging.basicConfig(level=logging.DEBUG)
# resolve_network_paths("tx",das=False,
#                       include_bank=False,
#                       include_events=False,
#                         include_stations=False,
#                         include_picks=False,
#                         include_travel_time=True,
#                       )


dataset = utdq.Dataset(das=False)
network = dataset.get_network(name="tx")
events = network.events
ebank = network.bank
ev_ids = events["event_id"].iloc[:5].tolist()
cat = ebank.get_events(event_id=ev_ids)

print(cat)
cat.apply_utdq_qc(debug=True,inplace=True)
print(cat)


# tt = network.travel_time
# print(network.events)
# print(tt)
# print(tt.predict(phase="P",distance= 30))

# network = dataset.get_network(name="GCI")
# network.plot_travel_time_qc(savepath=str(Path(__file__).parent / "GCI_travel_time_qc.png"),
#                             show_models=["travel_time_p50"])

# print(get_utdq_paths("GCI", das=True))

# bank_path = "/groups/igonin/ecastillo/UTDQuake_test/bank/GCI"
# bank = UTDQBank(bank_path)
# print(bank.db_paths)
# print(bank)

