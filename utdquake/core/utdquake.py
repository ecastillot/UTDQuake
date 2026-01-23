from __future__ import annotations

from pathlib import Path
from typing import Optional

from utdquake.cache import get_eventbank_path
from utdquake.hf_download import download_network_eventbank
from utdquake.eventbank import EventBank  # your subclass


def load_network(
    network: str,
    repo_id: str = "ecastillot/UTDQuakeDataset",
    repo_type: str = "dataset",
    revision: Optional[str] = None,
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
        "dataset" recommended.
    revision
        Optional branch/tag/commit.
    download_if_missing
        If True, download missing data automatically.

    Returns
    -------
    EventBank
        Local EventBank instance.
    """
    network = network.lower().strip()
    bank_path = get_eventbank_path(network)

    # You can decide what "exists" means (index file, etc.)
    exists = bank_path.exists() and any(bank_path.iterdir())

    if not exists:
        if not download_if_missing:
            raise FileNotFoundError(
                f"UTDQuake network '{network}' not found locally at: {bank_path}"
            )

        # Download into the bank_path directly
        download_network_eventbank(
            network=network,
            local_dir=bank_path,
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision,
        )

    return EventBank(str(bank_path))
