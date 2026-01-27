from utdquake.bank.bank import EventBank
import pandas as pd
from .cache import list_local_networks,list_remote_networks
from .path import get_root,get_eventbank_path
from .download import download_utdquake
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import os
import sqlite3
from pathlib import Path



class UTDQuake:
    def __init__(self, force_all: bool = False):
        """
        Initialize UTDQuake by collecting network paths only.
        EventBanks are not loaded yet.
        """
        self.base_path = get_root()
        self.network_paths = {}

        if force_all:
            self.networks = list_remote_networks()
        else:
            self.networks = list_local_networks()
        
        # Collect network paths
        for net in self.networks:  # do NOT load EventBank yet
            event_bank_path = get_eventbank_path(net)

            if not event_bank_path.exists() and force_all:
                print(f"Downloading missing network {net}...")
                download_utdquake(local_dir=self.base_path / "events", networks=[net])
            
            if event_bank_path.exists():
                self.network_paths[net] = event_bank_path
            else:
                print(f"Network path not found: {event_bank_path}")
        
        # Global bank will be built lazily
        self.global_bank = None

    def build_global(self):
        if self.global_bank is not None:
            return self.global_bank
        global_db = build_global_eventbank(self.network_paths, self.base_path)
        self.global_bank = EventBank(global_db)
        return self.global_bank

