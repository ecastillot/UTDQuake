# from datasets import Dataset, DatasetDict, load_from_disk
import pandas as pd
from pathlib import Path

from utdquake.core.config import ( PREF_PICKS_TYPES,PREF_EVENTS_TYPES,
                        PREF_STATIONS_TYPES,PREF_STATS_TYPES)


# print(PREF_PICKS_TYPES)
# print(PREF_EVENTS_TYPES)
# Example: paths to your local files
base_dir = Path("/groups/igonin/ecastillo/UTDQuake/manifests")

# Pick one network to test
network = "AEIC"
# events_file = base_dir / "events" / f"network={network}.parquet"
# stations_file = base_dir / "stations" / f"network={network}.parquet"
picks_file = base_dir / "picks" / f"network={network}.parquet"
# stats_file = base_dir / "network.parquet"

# Load parquet files with pandas
# df_stats = pd.read_parquet(stats_file)
# df_events = pd.read_parquet(events_file)
# df_stations = pd.read_parquet(stations_file)
df_picks = pd.read_parquet(picks_file)

# print("Stats DataFrame:", df_stats.info())
# print("Events DataFrame:", df_events.info())
# print("Stations DataFrame:", df_stations.info())
print(df_picks[["time_correction"]])
print("Picks DataFrame:", df_picks.info())

