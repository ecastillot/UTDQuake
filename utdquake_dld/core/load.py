from __future__ import annotations

from pathlib import Path
from typing import Optional
import shutil
import logging
from .path import get_eventbank_path, get_root
from .download import download_utdquake
from ..bank.bank import EventBank  
from .config import DEFAULT_REPO_ID, DEFAULT_REPO_TYPE

logger = logging.getLogger(__name__)


def load_network(
    network: str,
    repo_id: str = DEFAULT_REPO_ID,
    repo_type: str = DEFAULT_REPO_TYPE,
    download_if_missing: bool = True,
    max_retries: int = 3,
) -> EventBank:
    """
    Load a UTDQuake network EventBank.

    If the EventBank is not available locally, it is downloaded automatically.
    If the local bank exists but is incomplete/corrupted, it will be re-downloaded.

    Parameters
    ----------
    network
        Network name (e.g., "tx", "rsnc").
    repo_id
        Hugging Face repo id.
    repo_type
        DEFAULT_REPO_TYPE recommended.
    download_if_missing
        If True, download missing data automatically.
    max_retries
        Number of attempts to load/download the network.

    Returns
    -------
    EventBank
        Local EventBank instance.
    """
    network = network.strip()
    bank_path = get_eventbank_path(network)

    for attempt in range(1, max_retries + 1):
        exists = bank_path.exists() and any(bank_path.iterdir())

        if not exists:
            if not download_if_missing:
                raise FileNotFoundError(
                    f"UTDQuake network '{network}' not found locally at: {bank_path}"
                )

            download_utdquake(
                local_dir=get_root(),
                networks=network,
                repo_id=repo_id,
                repo_type=repo_type,
            )

        try:
            return EventBank(str(bank_path))
        except Exception:
            logger.error(
                "Failed to load EventBank for network '%s' (attempt %d/%d): Corrupted or incomplete data.",
                network,
                attempt,
                max_retries,
            )

            if attempt >= max_retries:
                raise RuntimeError(f"Failed to load network '{network}' after {max_retries} attempts.")

            # Remove partial/corrupted folder and retry download
            if bank_path.exists():
                logger.info(
                        "Removing partial/corrupted EventBank at '%s' and retrying download (attempt %d/%d)...",
                        bank_path,
                        attempt + 1,
                        max_retries,
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