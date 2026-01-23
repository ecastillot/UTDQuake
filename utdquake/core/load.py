from __future__ import annotations

from pathlib import Path
from typing import Optional

from .cache import get_eventbank_path, get_root
from .download import download_utdquake
from utdquake.bank.bank import EventBank  
from .config import DEFAULT_REPO_ID, DEFAULT_REPO_TYPE

def load_network(
    network: str,
    repo_id: str = DEFAULT_REPO_ID,
    repo_type: str = DEFAULT_REPO_TYPE,
    download_if_missing: bool = True,
) -> EventBank:
    """
    Load a UTDQuake network EventBank.

    If the EventBank is not available locally, it is downloaded automatically.

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

    Returns
    -------
    EventBank
        Local EventBank instance.
    """
    network = network.strip()
    bank_path = get_eventbank_path(network)

    # You can decide what "exists" means (index file, etc.)
    exists = bank_path.exists() and any(bank_path.iterdir())

    if not exists:
        if not download_if_missing:
            raise FileNotFoundError(
                f"UTDQuake network '{network}' not found locally at: {bank_path}"
            )

        # Download into the bank_path directly
        download_utdquake(
            local_dir=get_root(),
            networks=network,
            repo_id=repo_id,
            repo_type=repo_type,
        )

    return EventBank(str(bank_path))

def tx(**kwargs) -> EventBank:
    """Shortcut to load the TX EventBank."""
    return load_network("tx", **kwargs)


if __name__ == "__main__":
    # bank = load_network(network="tx")
    bank = tx()
    print(bank)