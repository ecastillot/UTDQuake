from __future__ import annotations

from pathlib import Path
from typing import Optional
import shutil
import pandas as pd
import logging
from .path import get_eventbank_path, get_root,get_manifest_file_path
from .download import download_utdquake
from utdquake.bank.bank import EventBank  
from .config import DEFAULT_REPO_ID, DEFAULT_REPO_TYPE

logger = logging.getLogger(__name__)


def load_network(
    network: str,
    repo_id: str = DEFAULT_REPO_ID,
    repo_type: str = DEFAULT_REPO_TYPE,
    bank: bool = True,
    events: bool = True,
    stations: bool = True,
    picks: bool = True,
    download_if_missing: bool = True,
    max_retries: int = 3,
) -> EventBank:
    """
    Load a UTDQuake network EventBank with optional validation of bank,
    events, stations, and picks. If the data is missing or corrupted,
    it will attempt to download it automatically.

    Parameters
    ----------
    network
        Network name (e.g., "tx", "rsnc").
    repo_id
        Hugging Face repo id.
    repo_type
        DEFAULT_REPO_TYPE recommended.
    bank
        Validate the EventBank folder (ZIPs extracted properly).
    events
        Validate the events manifest.
    stations
        Validate the stations manifest.
    picks
        Validate the picks manifest.
    download_if_missing
        Automatically download missing/corrupted data.
    max_retries
        Number of attempts to load/download the network.

    Returns
    -------
    EventBank
        Local EventBank instance.
    """
    network = network.strip()
    bank_path = get_eventbank_path(network)
    manifests = {
        "events": get_manifest_file_path(network, "events"),
        "stations": get_manifest_file_path(network, "stations"),
        "picks": get_manifest_file_path(network, "picks"),
    }

    for attempt in range(1, max_retries + 1):
        # --- Check existence ---
        exists = bank_path.exists() and any(bank_path.iterdir())
        manifests_ok = True

        if exists:
            # --- Validate manifests ---
            try:
                if events:
                    pd.read_parquet(manifests["events"], columns=[])
                if stations:
                    pd.read_parquet(manifests["stations"], columns=[])
                if picks:
                    pd.read_parquet(manifests["picks"], columns=[])
            except Exception as e:
                logger.warning("Manifest validation failed: %s", e)
                manifests_ok = False

        if not exists or not manifests_ok:
            if not download_if_missing:
                raise FileNotFoundError(
                    f"UTDQuake network '{network}' is missing or corrupted locally at: {bank_path}"
                )

            logger.info("Downloading network '%s' (attempt %d/%d)...", network, attempt, max_retries)
            download_utdquake(
                local_dir=get_root(),
                networks=network,
                repo_id=repo_id,
                repo_type=repo_type,
                bank=bank,
                events=events,
                stations=stations,
                picks=picks
            )

        try:
            # --- Try to load EventBank ---
            eb = EventBank(str(bank_path))
            logger.info("Network '%s' loaded successfully.", network)
            return eb
        except Exception as e:
            logger.error(
                "Failed to load EventBank for network '%s' (attempt %d/%d): %s",
                network,
                attempt,
                max_retries,
                e,
            )
            if attempt >= max_retries:
                raise RuntimeError(f"Failed to load network '{network}' after {max_retries} attempts.")

            # Remove partial/corrupted folder and retry download
            if bank_path.exists():
                logger.info(
                    "Removing partial/corrupted EventBank at '%s' and retrying download...",
                    bank_path
                )
                shutil.rmtree(bank_path, ignore_errors=True)

    raise RuntimeError(f"Failed to load network '{network}' after {max_retries} attempts.")

def tx(**kwargs) -> EventBank:
    """Shortcut to load the TX EventBank."""
    return load_network("tx", **kwargs)


if __name__ == "__main__":
    # bank = load_network(network="tx")
    bank = tx()
    print(bank)