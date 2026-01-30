import os
import logging
import zipfile
from pathlib import Path
from datasets import load_dataset, Dataset, IterableDataset
from typing import Union, List, Optional
from huggingface_hub import snapshot_download
from .config import HF_REPO_ID, HF_REPO_TYPE,HF_CONFIG

logger = logging.getLogger(__name__)

def download_snapshot(
    local_dir: Union[str, Path],
    networks: Union[str, List[str]],
    include_banks: bool = True,
    include_networks: bool = True,
    include_events: bool = True,
    include_stations: bool = True,
    include_picks: bool = True,
    overwrite: bool = True,
    unzip_banks: bool = True
) -> Path:
    """
    Download selected data from the UTDQuake Hugging Face repository.

    Parameters
    ----------
    local_dir : str or Path
        Local directory where the data will be downloaded. Created if it does not exist.
    networks : str or list of str
        Networks to download:
        - "*" downloads all networks
        - "t*" downloads all networks starting with 't'
        - ["tx", "uw"] downloads only specified networks
    include_banks : bool, optional
        Whether to download the bank (synthetic) data. Default: True.
    include_networks : bool, optional
        Whether to download the network metadata. Default: True.
    include_events : bool, optional
        Whether to download the events data. Default: True.
    include_stations : bool, optional
        Whether to download station metadata. Default: True.
    include_picks : bool, optional
        Whether to download seismic picks. Default: True.
    overwrite : bool, optional
        If True, existing files will be re-downloaded. Default: True.
    unzip_banks : bool, optional
        If True, downloaded bank zip files will be automatically extracted. Default: True.

    Returns
    -------
    Path
        Path to the local directory containing the downloaded snapshot.

    Notes
    -----
    The function builds a set of allowed file patterns based on the requested networks and data types.
    Only files matching these patterns are downloaded. Zip files in banks are optionally unzipped.
    
    Examples
    --------
    >>> download_snapshot("/tmp/utdquake", networks=["tx", "uw"], include_picks=False)
    >>> download_snapshot("/tmp/utdquake", networks="*", overwrite=False)
    """
    repo_id = HF_REPO_ID
    repo_type = HF_REPO_TYPE

    # Ensure local directory exists
    os.makedirs(local_dir, exist_ok=True)

    # Convert single string input into a list
    if isinstance(networks, str):
        networks = [networks]

    # Dictionary to check which data types to include
    include = {
            "banks": include_banks,
            "events": include_events,
            "stations": include_stations,
            "picks": include_picks,
        }

    # Build allow_patterns for snapshot_download
    allow_patterns = []
    for net in networks:
        for key, enabled in include.items():
            if not enabled:
                continue
            cfg = HF_CONFIG[key]
            path_to_check = Path(local_dir) / cfg.path.format(network=net)

            if overwrite or not path_to_check.exists():
                allow_patterns.append(cfg.path.format(network=net))

    # Always include networks metadata if requested
    if include_networks:
        network_path = Path(local_dir) / HF_CONFIG["networks"].path
        # Only append if file does not exist, or overwrite is True
        if overwrite or not network_path.exists():
            allow_patterns.append(HF_CONFIG["networks"].path)

    # Logging for debug
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

    # Optionally unzip bank files
    if include_banks:
        if unzip_banks:
            for net in networks:
                # Unzip downloaded files and remove .zip
                zip_paths = HF_CONFIG["banks"].path.format(network=net)
                for zip_file in Path(local_dir).glob(zip_paths):
                    logger.info("Unzipping %s...", zip_file)
                    with zipfile.ZipFile(zip_file, "r") as zip_ref:
                        zip_ref.extractall(zip_file.parent)
                    zip_file.unlink()  # remove .zip
                    logger.info("Removed %s", zip_file)

    logger.info("Extraction complete!")

    return Path(local_dir)


def load(
    key: str,
    network: Optional[Union[str, List[str]]] = None,
    streaming: bool = False,
    **kwargs
) -> Union[Dataset, IterableDataset]:
    """
    Load a dataset from the UTDQuake Hugging Face repository.

    Parameters
    ----------
    key : str
        Dataset key. Must be one of "networks", "stations", "events", "picks".
    network : str or list of str, optional
        Network code(s) to filter. Use "*" for all networks.
        Ignored if key == "networks".
    streaming : bool, optional
        If True, loads dataset in streaming mode (lazy iteration).
    **kwargs : dict
        Additional keyword arguments forwarded to `datasets.load_dataset`.

    Returns
    -------
    Dataset or IterableDataset
        Loaded Hugging Face dataset. Type depends on `streaming`.

    Raises
    ------
    ValueError
        If `key` is not one of the supported dataset types.

    Notes
    -----
    - When `key` is "networks", the `network` parameter is ignored.
    - For other keys, the `network` argument filters the files to load.
    - Supports both single network (str) and multiple networks (list of str).
    
    Examples
    --------
    >>> ds = load("stations", network="tx")
    >>> ds = load("events", network=["tx","uw"], streaming=True)
    """
    if key not in HF_CONFIG:
        raise ValueError(f"Unknown key '{key}'. Must be one of {list(HF_CONFIG.keys())}.")

    # Handle data_files
    data_files = None
    if key != "network" and network is not None:
        # Normalize network to list
        if isinstance(network, str):
            network = [network]

        network_paths = [HF_CONFIG[key].path.format(network=net) for net in network] \
                        if isinstance(network, list) \
                        else [HF_CONFIG[key].path]

        data_files = {HF_CONFIG[key].split: network_paths }

    dataset = load_dataset(
        HF_REPO_ID,
        name=HF_CONFIG[key].name,
        split=HF_CONFIG[key].split,
        data_files=data_files,
        streaming=streaming,
        **kwargs
    )
    return dataset
