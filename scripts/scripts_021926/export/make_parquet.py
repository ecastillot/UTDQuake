import os
# Set root
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

import logging
from utdquake.utils.cache import list_local_networks
from utdquake.core.obspy import EventBank
import concurrent.futures as cf


logging.basicConfig(level=logging.INFO)

# Path to export
export_path = "/groups/igonin/ecastillo/bck_utdq/test_021926"
workers = None  # Number of concurrent workers for exporting

# Get all banks
banks = list_local_networks("bank")
# banks = {"RSNC":banks["RSNC"]}  # Test with a single bank first


def export_bank(bank_name: str):
    """
    Load a bank and export it to Parquet.
    """
    try:
        logging.info(f"Exporting bank '{bank_name}'...")
        eb = EventBank(banks[bank_name])
        eb.to_parquet(export_path,qc_debug=True)
        logging.info(f"Bank '{bank_name}' exported successfully.")
    except Exception as e:
        logging.error(f"Failed to export bank '{bank_name}': {e}")


# Use ThreadPoolExecutor to do all banks concurrently
with cf.ThreadPoolExecutor(workers) as executor:
    # Map each bank name to export_bank function
    list(executor.map(export_bank, banks.keys()))