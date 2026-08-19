from pathlib import Path
from ..core.config import get_root

def list_local_networks(data_type: str, das: bool = False) -> dict[str, Path]:
    """
    Return all networks available locally as a dictionary.

    For 'bank', returns folders containing at least one file.  
    For other data types, returns parquet files, removing the 'network='
    prefix and '.parquet' suffix to get the network name.

    Parameters
    ----------
    data_type : str
        Type of data to check for ('bank', 'events', 'stations', 'picks').
    das: bool, optional
        Whether to use the DAS dataset paths. Default is False.

    Returns
    -------
    dict[str, Path]
        Dictionary where keys are network names and values are Paths:
        - For 'bank', the folder Path
        - For other data types, the Path to the parquet file
    """
    root = get_root(das=das) / ("banks" if data_type == "bank" else data_type)
    if not root.exists():
        return {}

    network_dict: dict[str, Path] = {}

    if data_type == "bank":
        # Only folders that are not empty
        for p in root.iterdir():
            if p.is_dir() and any(p.iterdir()):
                network_dict[p.name] = p
    else:
        # Files ending with .parquet
        for p in root.iterdir():
            if p.is_file() and p.suffix == ".parquet":
                # Remove prefix 'network=' and suffix '.parquet' for key
                name = p.stem
                if name.startswith("network="):
                    name = name[len("network="):]
                network_dict[name] = p

    # Sort by key (network name)
    return dict(sorted(network_dict.items()))