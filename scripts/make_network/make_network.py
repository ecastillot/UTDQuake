import os
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"


from manager import UTDQBank
from parquet import build_manifests
import logging

logging.basicConfig(level=logging.INFO)


# bank_path =  "/groups/igonin/ecastillo/UTDQuake/bank/ak"
# bank = UTDQBank(bank_path)
# summary = bank.get_summary_from_parquets()
# print(summary)

build_manifests()