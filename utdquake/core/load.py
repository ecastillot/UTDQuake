from __future__ import annotations

import obsplus
import logging 
import shutil
import logging
import pyarrow.parquet as pq
from .data import download_snapshot
from .config import get_root,HF_CONFIG

logger = logging.getLogger(__name__)


def validate_eventbank(path) -> bool:
    if not path.exists():
        return False
    try:
        bank = obsplus.EventBank(str(path))
        bank.read_index()
        return True
    except Exception:
        return False

def validate_parquet(path) -> bool:
    if not path.exists():
        return False
    try:
        pq.ParquetFile(path)
        return True
    except Exception:
        return False

def resolve_missing_components(
    bank_path,
    parquets,
    flags,
    include_bank
) -> set:

    missing = set()

    for key, path in parquets.items():
        if flags[key] and not validate_parquet(path):
            missing.add(key)

    if include_bank:
        #  DEBUG HERE
        logger.debug("bank_path = %s", bank_path)
        logger.debug("bank_path exists = %s", bank_path.exists())
        if bank_path.exists():
            logger.debug("bank_path contents = %s", list(bank_path.iterdir()))

        if not validate_eventbank(bank_path):
            missing.add("banks")

    return missing

def cleanup_components(to_download, bank_path, parquets):
    if "banks" in to_download:
        shutil.rmtree(bank_path, ignore_errors=True)

    for key in ("events", "stations", "picks"):
        if key in to_download:
            path = parquets[key]
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

def resolve_network_paths(
    network: str,
    include_bank: bool = True,
    include_events: bool = True,
    include_stations: bool = True,
    include_picks: bool = True,
    max_retries: int = 2,
) -> dict:
    """
    Ensure network data exists locally and return paths.
    """

    network = network.strip()

    bank_path = get_root() / "bank" / network
    parquets = {
        "events": get_root() / HF_CONFIG["events"].path.format(network=network),
        "stations": get_root() / HF_CONFIG["stations"].path.format(network=network),
        "picks": get_root() / HF_CONFIG["picks"].path.format(network=network),
    }

    flags = {
        "events": include_events,
        "stations": include_stations,
        "picks": include_picks,
    }

    for attempt in range(max_retries):

        missing = resolve_missing_components(
            bank_path, parquets, flags, include_bank
        )

        if not missing:
            return {
                **({"bank": bank_path} if include_bank else {}),
                **{k: v for k, v in parquets.items() if flags[k]},
            }

        logger.info(
            "Resolving network '%s' (attempt %d/%d). Missing: %s",
            network, attempt + 1, max_retries, missing
        )

        cleanup_components(missing, bank_path, parquets)

        download_snapshot(
            local_dir=get_root(),
            networks=network,
            include_banks="banks" in missing,
            include_events="events" in missing,
            include_stations="stations" in missing,
            include_picks="picks" in missing,
            unzip_banks=True,
        )

    raise RuntimeError(
        f"Could not resolve network '{network}' after {max_retries} attempts"
    )

                
