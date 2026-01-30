from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict, Set

import obsplus
import pyarrow.parquet as pq
from .data import download_snapshot
from .config import get_root, HF_CONFIG

logger = logging.getLogger(__name__)


def validate_eventbank(path: Path) -> bool:
    """
    Validate that a path contains a readable ObsPlus EventBank.

    Parameters
    ----------
    path : Path
        Path to the EventBank directory.

    Returns
    -------
    bool
        True if the EventBank exists and is readable, False otherwise.
    """
    if not path.exists():
        return False
    try:
        bank = obsplus.EventBank(str(path))
        bank.read_index()
        return True
    except Exception:
        return False

def validate_parquet(path: Path) -> bool:
    """
    Validate that a path contains a valid Parquet file.

    Parameters
    ----------
    path : Path
        Path to the Parquet file.

    Returns
    -------
    bool
        True if the file exists and can be read by PyArrow, False otherwise.
    """
    if not path.exists():
        return False
    try:
        pq.ParquetFile(path)
        return True
    except Exception:
        return False

def resolve_missing_components(
    bank_path: Path,
    parquets: Dict[str, Path],
    flags: Dict[str, bool],
    include_bank: bool
) -> Set[str]:
    """
    Determine which components are missing or invalid locally.

    Parameters
    ----------
    bank_path : Path
        Path to the EventBank directory.
    parquets : dict
        Dictionary of Parquet file paths for keys 'events', 'stations', 'picks'.
    flags : dict
        Dictionary indicating which components to check.
    include_bank : bool
        Whether to include bank validation.

    Returns
    -------
    set
        Set of missing components (keys) that need to be downloaded.
    """

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

def cleanup_components(to_download: Set[str], bank_path: Path, parquets: Dict[str, Path]) -> None:
    """
    Remove local files/directories for components that will be re-downloaded.

    Parameters
    ----------
    to_download : set
        Components to remove ('banks', 'events', 'stations', 'picks').
    bank_path : Path
        Path to the EventBank directory.
    parquets : dict
        Dictionary of Parquet file paths.
    """
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
) -> Dict[str, Path]:
    """
    Ensure that all network data components exist locally and return their paths.

    If any required components are missing or invalid, attempts to download them
    using `download_snapshot`. Raises RuntimeError if unable to resolve after retries.

    Parameters
    ----------
    network : str
        Network code to resolve.
    include_bank : bool, optional
        Whether to include EventBank. Default is True.
    include_events : bool, optional
        Whether to include event Parquet. Default is True.
    include_stations : bool, optional
        Whether to include stations Parquet. Default is True.
    include_picks : bool, optional
        Whether to include picks Parquet. Default is True.
    max_retries : int, optional
        Maximum number of download attempts. Default is 2.

    Returns
    -------
    dict
        Dictionary of component paths. Keys include 'bank', 'events', 'stations', 'picks'.

    Raises
    ------
    RuntimeError
        If network data could not be resolved after `max_retries` attempts.
    """
    network = network.strip()

    # Paths for EventBank and Parquet components
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

        # Remove invalid/missing components before redownloading
        cleanup_components(missing, bank_path, parquets)

        # Download missing components
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

                
