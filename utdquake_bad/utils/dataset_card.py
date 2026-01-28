import os
import yaml
from typing import Literal, List, Dict

def generate_config_type(manifests_folder: str, types: List[str]) -> List[Dict]:
    """
    Generate configs where each config is a type (stations, events, picks).
    Returns list of configs.
    """
    configs = []

    for i, t in enumerate(types, 1):
        folder = os.path.join(manifests_folder, t)
        paths = []

        if os.path.exists(folder):
            for file in sorted(os.listdir(folder)):
                if file.endswith(".parquet"):
                    paths.append(os.path.join("manifests", t, file))

        if not paths:
            continue

        configs.append(
            {
                "config_name": f"{i}_{t}",
                "data_files": [
                    {
                        "split": "all",
                        "path": paths,
                    }
                ],
            }
        )
    return configs


def generate_config_network(manifests_folder: str, types: List[str]) -> List[Dict]:
    """
    Generate configs where each config is a network.
    Splits are the types (stations, events, picks)
    """
    configs = []

    # discover networks from stations folder (assuming all networks have a station file)
    station_folder = os.path.join(manifests_folder, "stations")
    networks = []

    if os.path.exists(station_folder):
        for file in os.listdir(station_folder):
            if file.endswith(".parquet") and "network=" in file:
                networks.append(file.split("network=")[-1].replace(".parquet", ""))

    for net in sorted(networks):
        data_files = []
        for t in types:
            p = os.path.join("manifests", t, f"network={net}.parquet")
            if os.path.exists(os.path.join(manifests_folder, t, f"network={net}.parquet")):
                data_files.append(
                    {"split": t, "path": p}
                )
        if data_files:
            configs.append(
                {
                    "config_name": net,
                    "data_files": data_files,
                }
            )
    return configs


def generate_hf_manifest(
    manifests_folder: str,
    output_file: str,
    config: Literal["type", "network"] = "type",
    split: Literal["all", "network"] = "all"
) -> None:
    """
    Generate Hugging Face YAML manifest.
    
    Parameters:
        config: "type" -> configs are stations/events/picks
                "network" -> configs are networks
        split:  currently placeholder (future extensions, e.g., time-based splits)
    """
    types = ["stations", "events", "picks"]

    # always keep global stats config
    configs = [
        {
            "config_name": "0_network",
            "data_files": [
                {
                    "split": "stats",
                    "path": os.path.join("manifests", "stats.parquet"),
                }
            ],
        }
    ]

    if config == "type":
        configs += generate_config_type(manifests_folder, types)
    elif config == "network":
        configs += generate_config_network(manifests_folder, types)
    else:
        raise ValueError(f"Unknown config='{config}'")

    with open(output_file, "w") as f:
        yaml.dump(configs, f, sort_keys=False)

    print(f"Hugging Face YAML manifest saved to {output_file}")