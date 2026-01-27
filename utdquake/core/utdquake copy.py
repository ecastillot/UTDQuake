from utdquake.bank.bank import EventBank
import pandas as pd
from .cache import get_root,list_local_networks,get_eventbank_path,list_remote_networks
from .download import download_utdquake
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import os

class UTDQuake:
    def __init__(self,force_all: bool = False):
        """
        base_path: path to UTDQuake/events/
        """
        self.base_path = get_root()
        self.networks = {}

        if force_all:
            networks = list_remote_networks()
        else:
            networks = list_local_networks()
        
        # Load all networks automatically
        for net in networks():  # could scan folders dynamically
            event_bank_path = get_eventbank_path(net)

            if not event_bank_path.exists():
                print(f"Network path does not exist: {event_bank_path}")
                
                if force_all:
                    print(f"Attempting to download network {net}...")
                    download_utdquake(local_dir=self.base_path / "events", networks=[net])

            try:
                self.networks[net] = EventBank(event_bank_path )
            except Exception as e:
                print(f"Failed to load network {net}: {e}")

    def read_index(self, max_workers: int = None) -> pd.DataFrame:
        """Return a merged index of all networks in parallel with progress bar"""
        
        def load_network_index(net_bank_pair):
            net, bank = net_bank_pair
            df = bank.read_index()
            df["network"] = net  # optional: track origin
            #network column first
            cols = df.columns.tolist()
            cols = ["network"] + [col for col in cols if col != "network"]
            return df

        network_items = list(self.networks.items())
        
        if max_workers is None:
            max_workers = min(12, os.cpu_count() or 4)

        dfs = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # map returns an iterator, wrap it with tqdm
            for df in tqdm(executor.map(load_network_index, network_items),
                        total=len(network_items),
                        desc="Loading network indices"):
                dfs.append(df)
        
        return pd.concat(dfs, ignore_index=True)

    def read_event(self, event_id: str):
        """Try reading an event from all banks"""
        for bank in self.networks.values():
            try:
                return bank.read_event(event_id)
            except KeyError:
                continue
        raise KeyError(f"Event {event_id} not found in any network")

    def query(self, *args, **kwargs) -> pd.DataFrame:
        """Query all networks and merge results"""
        dfs = [bank.query(*args, **kwargs) for bank in self.networks.values()]
        return pd.concat(dfs, ignore_index=True)