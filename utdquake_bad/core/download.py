import os
import zipfile
from huggingface_hub import snapshot_download
from pathlib import Path
from .config import DEFAULT_REPO_ID, DEFAULT_REPO_TYPE
import logging

logger = logging.getLogger(__name__)

def download_utdquake(local_dir, networks, repo_id: str = DEFAULT_REPO_ID,
                        repo_type: str = DEFAULT_REPO_TYPE,
                        bank: bool = True,
                        events: bool = True,
                        stations:bool = True,
                        picks: bool = True) -> Path:
    """
    Download selected Texas (TX) data from the UTDQuake Hugging Face repository.

    Parameters
    ----------
    local_dir : str
        Local directory where the data will be downloaded.
    networks : str or list of str
        Networks to download:
        - "*" downloads all networks
        - "t*" downloads all networks starting with 't'
        - ["tx", "uw"] downloads only specified networks
    repo_id : str
        Hugging Face repository ID (default: DEFAULT_REPO_ID).
    repo_type : str
        Type of repository (default: DEFAULT_REPO_TYPE).
    Returns
    -------
    Path
        Path to the downloaded folder.
    """

    # Ensure local directory exists
    os.makedirs(local_dir, exist_ok=True)

    # Convert single string input into a list
    if isinstance(networks, str):
        networks = [networks]


    # Build allow_patterns for snapshot_download
    allow_patterns = []
    for net in networks:
        # Wildcard support
        if bank:
            bank_pattern = f"events/{net}.zip" if "*" not in net else f"events/{net}.zip"
            allow_patterns.append(bank_pattern)
        if events:
            events_pattern = f"manifests/events/network={net}.parquet"
            allow_patterns.append(events_pattern)
        if stations:
            stations_pattern = f"manifests/stations/network={net}.parquet"
            allow_patterns.append(stations_pattern)
        if picks:
            picks_pattern = f"manifests/picks/network={net}.parquet"
            allow_patterns.append(picks_pattern)

    logger.info("Downloading data from: %s", repo_id)
    logger.info("Saving into: %s", os.path.abspath(local_dir))
    logger.info("Allow patterns: %s", allow_patterns)

    # Download files matching allow_patterns
    path = snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        repo_type=repo_type,
        allow_patterns=allow_patterns,
        max_workers=1,
    )

    if bank:
        # Unzip downloaded files and remove .zip
        for zip_file in Path(local_dir).glob("events/*.zip"):
            logger.info("Unzipping %s...", zip_file)
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(zip_file.parent)
            zip_file.unlink()  # remove .zip
            logger.info("Removed %s", zip_file)

    logger.info("Extraction complete!")

    return Path(local_dir)


if __name__ == "__main__":
    local_path = "/groups/igonin/ecastillo/test"
    download_utdquake(local_path,networks="RSNC")