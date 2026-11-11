import os
import logging
import zipfile
from pathlib import Path
from datasets import load_dataset, Dataset, IterableDataset
from typing import Union, List, Optional
from huggingface_hub import snapshot_download
from .config import HF_REPO_ID, HF_REPO_TYPE, get_hf_entry, get_revision, get_root, HF_CONFIG, read_snapshot, write_snapshot
from .utils import renamed_kwarg

logger = logging.getLogger(__name__)

def download_snapshot(
    local_dir: Union[str, Path],
    utdq_nets: Union[str, List[str]] = None,
    das: bool = False,
    include_banks: bool = False,
    include_networks: bool = True,
    include_events: bool = True,
    include_stations: bool = True,
    include_picks: bool = True,
    include_travel_time: bool = False,
    overwrite: bool = True,
    unzip_banks: bool = True,
    networks: Union[str, List[str]] = None,
    revision: Optional[str] = None,
) -> Path:
    """
    Download selected data from the UTDQuake Hugging Face repository.

    Parameters
    ----------
    local_dir : str or Path
        Local directory where the data will be downloaded. Created if it does not exist.
    utdq_nets : str or list of str
        UTDQuake networks (``utdq_net`` codes) to download:
        - "*" downloads all networks
        - "t*" downloads all networks starting with 't'
        - ["tx", "uw"] downloads only specified networks
    das : bool, optional
        If True, downloads from the DAS dataset paths. Default: False (standard paths).
    include_banks : bool, optional
        Whether to download the QuakeML banks (zipped, much larger than the tables: about 20 GB for all
        networks in v2.0). Default: False; ``Network(...).bank`` downloads a network's bank when it is first
        used.
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
    networks : str or list of str, optional
        Deprecated alias of ``utdq_nets``.
    revision : str, optional
        Hugging Face revision to download (branch, tag such as ``v1.0``,
        commit hash or ``refs/pr/N``). Default: the ``UTDQUAKE_REVISION``
        environment variable, else ``main``.

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
    >>> download_snapshot("/tmp/utdquake", utdq_nets=["tx", "uw"], include_picks=False)
    >>> download_snapshot("/tmp/utdquake", utdq_nets="*", overwrite=False)
    """
    repo_id = HF_REPO_ID
    repo_type = HF_REPO_TYPE
    networks = renamed_kwarg(utdq_nets, networks, "utdq_nets", "networks", "download_snapshot")
    if networks is None:
        raise TypeError("download_snapshot() missing required argument: 'utdq_nets'")

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
            ".utdquake/travel_time": include_travel_time
        }

    # Build allow_patterns for snapshot_download
    allow_patterns = []
    for net in networks:
        for key, enabled in include.items():
            if not enabled:
                continue
            cfg = get_hf_entry(key,das)
            path_to_check = Path(local_dir) / cfg.path.format(utdq_net=net)

            if overwrite or not path_to_check.exists():
                allow_patterns.append(cfg.path.format(utdq_net=net))

    # Always include networks metadata if requested
    if include_networks:
        network_path = Path(local_dir) / get_hf_entry("networks",das).path
        # Only append if file does not exist, or overwrite is True
        if overwrite or not network_path.exists():
            allow_patterns.append(get_hf_entry("networks",das).path)

    # Logging for debug
    revision = get_revision(revision)
    logger.info("Downloading data from: %s%s", repo_id, f" (revision {revision})" if revision else "")
    logger.info("Saving into: %s", os.path.abspath(local_dir))
    logger.info("Allow patterns: %s", allow_patterns)

    # a root holds one dataset version: warn before mixing files of another version into it
    before = read_snapshot(local_dir)
    if before is not None and before.get("revision") != (revision or "main"):
        logger.warning("%s holds files of dataset version %s; downloading %s into it mixes versions (files already "
                       "there are not replaced unless overwrite=True). Use another root (UTDQUAKE_ROOT) or the "
                       "default cache, which has one folder per version.", local_dir, before.get("revision"),
                       revision or "main")

    # Download files matching allow_patterns
    path = snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        repo_type=repo_type,
        allow_patterns=allow_patterns,
        revision=revision,
        max_workers=1,
    )

    # Optionally unzip bank files
    if include_banks:
        if unzip_banks:
            for net in networks:
                # Unzip downloaded files and remove .zip
                zip_paths = get_hf_entry("banks",das).path.format(utdq_net=net)
                for zip_file in Path(local_dir).glob(zip_paths):
                    logger.info("Unzipping %s...", zip_file)
                    with zipfile.ZipFile(zip_file, "r") as zip_ref:
                        zip_ref.extractall(zip_file.parent)
                    zip_file.unlink()  # remove .zip
                    logger.info("Removed %s", zip_file)

    logger.info("Extraction complete!")

    commit = None
    try:
        from huggingface_hub import HfApi
        commit = HfApi().dataset_info(repo_id, revision=revision).sha
    except Exception:                      # offline: the version is still recorded
        pass
    if before is None or before.get("revision") == (revision or "main"):
        write_snapshot(local_dir, revision, commit)

    return Path(local_dir)


def load(
    key: str,
    utdq_net: Optional[Union[str, List[str]]] = None,
    streaming: bool = False,
    das: bool = False,
    network: Optional[Union[str, List[str]]] = None,
    revision: Optional[str] = None,
    **kwargs
) -> Union[Dataset, IterableDataset]:
    """
    Load a dataset from the UTDQuake Hugging Face repository.

    Parameters
    ----------
    key : str
        Dataset key. Must be one of "networks", "stations", "events", "picks".
    utdq_net : str or list of str, optional
        UTDQuake network code(s) to filter. Use "*" for all networks.
        Ignored if key == "networks".
    das : bool, optional
        if das is True, loads from the DAS cache root instead of the standard cache root.
    streaming : bool, optional
        If True, loads dataset in streaming mode (lazy iteration).
    network : str or list of str, optional
        Deprecated alias of ``utdq_net``.
    revision : str, optional
        Hugging Face revision to read (branch, tag such as ``v1.0``, commit
        hash or ``refs/pr/N``). Default: the ``UTDQUAKE_REVISION`` environment
        variable, else ``main``.
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
    - When `key` is "networks", the `utdq_net` parameter is ignored.
    - For other keys, the `utdq_net` argument filters the files to load.
    - Supports both single network (str) and multiple networks (list of str).
    - If the Hub cannot be reached (e.g. offline, ``HF_HUB_OFFLINE=1``), the
      files already under the local root (see :func:`download_snapshot` and
      ``UTDQUAKE_ROOT``) are read instead, with a warning.
    
    Examples
    --------
    >>> ds = load("stations", utdq_net="tx")
    >>> ds = load("events", utdq_net=["tx","uw"], streaming=True)
    """
    network = renamed_kwarg(utdq_net, network, "utdq_net", "network", "load")
    if key not in HF_CONFIG:
        raise ValueError(f"Unknown key '{key}'. Must be one of {list(HF_CONFIG.keys())}.")

    # Handle data_files
    data_files = None
    if key != "networks" and network is not None:
        # Normalize network to list
        if isinstance(network, str):
            network = [network]

        network_paths = [get_hf_entry(key,das).path.format(utdq_net=net) for net in network] \
                        if isinstance(network, list) \
                        else [get_hf_entry(key,das).path]

        data_files = {get_hf_entry(key,das).split: network_paths }

    try:
        dataset = load_dataset(
            HF_REPO_ID,
            name=get_hf_entry(key,das).name,
            split=get_hf_entry(key,das).split,
            data_files=data_files,
            streaming=streaming,
            revision=get_revision(revision),
            **kwargs
        )
    except Exception as e:
        # offline or Hub unreachable: read the copy under the local root
        # (e.g. after Dataset.download), same type of object as from the Hub
        local = _load_local(key, network, das, streaming)
        if local is None:
            raise
        logger.warning("Could not read %s from the Hugging Face Hub (%s); using the local copy under %s.",
                       key, type(e).__name__, get_root(das=das))
        return local
    return dataset


def _load_local(key: str, utdq_net, das: bool, streaming: bool):
    """``key`` from the local root as a ``datasets`` object, or None if no local file matches."""
    root = get_root(das=das)
    entry = get_hf_entry(key, das)
    if key == "networks" or utdq_net is None:
        patterns = [entry.path] if key == "networks" else [entry.path.format(utdq_net="*")]
    else:
        nets = [utdq_net] if isinstance(utdq_net, str) else list(utdq_net)
        patterns = [entry.path.format(utdq_net=n) for n in nets]
    files = sorted({str(f) for pattern in patterns for f in root.glob(pattern)})
    if not files:
        return None
    return load_dataset("parquet", data_files={entry.split: files}, split=entry.split, streaming=streaming)
