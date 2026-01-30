"""
UTDQuake Dataset Module
=======================

Provides high-level access to UTDQuake seismic data, including networks, 
stations, events, and picks. This module defines two main classes:

- `Dataset`: Access all networks, stations, and events. Provides dataset-wide
  summaries and plotting utilities.
- `Network`: Access network-specific data, including EventBank, stations,
  events, and picks. Provides network-level plotting and analysis.

Usage
-----

Basic usage:

>>> from utdquake.dataset import Dataset
>>> ds = Dataset()
>>> ds.networks.head()
>>> ds.stations.head()
>>> ds.events.head()

Access a single network:

>>> net = ds.get_network("tx01")
>>> net.stations.head()
>>> net.plot_overview()

Plotting:

>>> net.plot_stats(savepath="network_stats.png")
>>> ds.plot_overview(show=True)

Notes
-----

- Data is cached locally under the directory returned by `get_root()`.
- Network data is automatically downloaded if missing.
- Requires ObsPlus, Pandas, and plotting dependencies (Matplotlib, Seaborn, Cartopy).

"""

import obsplus
import pandas as pd
from .data import download_snapshot,load
from .load import resolve_network_paths
from .config import HF_CONFIG, get_root
from ..utils.utils import get_network_summary
from ..utils.plot import (plot_overview,
                          plot_stats,
                          plot_pick_histograms,
                          plot_pick_stats,
                          plot_station_location_uncertainty,
                          plot_uncertainty_boxplots,
                          plot_utdq_overview
                          )

class Dataset:
    """
    High-level interface for the UTDQuake dataset.

    Provides access to networks, stations, events, and picks.
    Allows plotting and summary analysis of the dataset.
    """

    def __init__(self):
        """Initialize Dataset with root cache directory."""
        self.root = get_root()

    def __str__(self) -> str:
        """Return a simple string representation."""
        return f"UTDQuake(root={self.root})"

    @property
    def description(self) -> str:
        """
        Return a summary of the dataset.

        Returns
        -------
        str
            Summary of networks, stations, and events.
        """
        return get_network_summary(stations=self.stations, 
                                    events= self.events)

    @property
    def networks(self):
        """Return all networks as a Pandas DataFrame."""
        return load(key="networks",network="*").to_pandas()

    @property
    def stations(self):
        """Return all stations as a Pandas DataFrame."""
        return load(key="stations",network="*").to_pandas()
    
    @property
    def events(self):
        """Return all events as a Pandas DataFrame."""
        return load(key="events",network="*").to_pandas()
    
    def get_events(self,network="*",streaming=False,**kwargs):
        """Return events for a specific network."""
        return load(key="networks",network=network,
                    streaming=streaming,**kwargs)
    
    def get_stations(self,network="*", streaming: bool=False,
                     **kwargs):
        """Return stations for a specific network."""
        return load(key="stations",network=network,
                    streaming=streaming,**kwargs)
    
    def get_picks(self,network="*", streaming: bool=True):
        """Return picks for a specific network."""
        return load(key="picks",network=network,
                    streaming=streaming)
    
    def get_local_networks(self, force_download: bool=False) -> pd.DataFrame:
        """
        Return locally cached networks, optionally forcing download.

        Parameters
        ----------
        force_download : bool
            If True, forces re-download of network metadata.

        Returns
        -------
        pd.DataFrame
            Network metadata as a DataFrame.
        """
        networks_path = self.root / HF_CONFIG["networks"].path

        needs_download = force_download or not networks_path.exists()

        if needs_download:
            download_snapshot(
                local_dir=self.root,
                networks="*",
                include_networks=True,
                include_banks=False,
                include_events=False,
                include_stations=False,
                include_picks=False,
            )
        return pd.read_parquet(networks_path)
    
    def get_network(self, name: str):
        """Return a Network object for a given network name."""
        return Network(name)
    
    def plot_overview(self, savepath=None, show=True):
        """
        Plot a comprehensive overview of UTDQuake dataset.

        Includes events, stations, and summary analysis.

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """
        plot_utdq_overview(events=self.events,
                            stations=self.stations,
                            analysis=self.description,
                            savepath=savepath,
                            show=show)

class Network:

    def __init__(self, name: str):
        """
        Represents a single network in UTDQuake.

        Provides access to network-specific events, stations, picks,
        EventBank, and plotting utilities.
        """
        self.name = name.strip() 

    def __str__(self, extended: bool = False) -> str:
        """
        Return a string representation of the network.

        Parameters
        ----------
        extended : bool
            If True, show all available details. Default is False.

        Returns
        -------
        str
        """
        description = self.description
        msg = f"Network({self.name})"

        if not extended:
            events = description.get("events", "N/A")
            stations = description.get("total_stations", "N/A")
            msg += f" | Events: {events}, Stations: {stations}"
        else:
            details = "\n".join(
                f"  {key}: {value}" 
                for key, value in description.items() 
                if key != "network"
            )
            msg += f"\n{details}"

        return msg
    
    @property
    def description(self) -> str:
        """
        Return a description dictionary of the network.

        Returns
        -------
        dict
            Keys include 'events', 'total_stations', and metadata fields.
        """
        networks_df = Dataset().get_local_networks(force_download=False)
        # networks_df = Dataset().networks.to_pandas()
        network_row = networks_df[networks_df["network"] == self.name]
        if network_row.empty:
            return f"Network '{self.name}' not found."
        network_series = network_row.iloc[0]
        return network_series.to_dict()

    @property
    def bank(self) -> obsplus.EventBank:
        """Return the ObsPlus EventBank for this network."""
        paths = resolve_network_paths(self.name, include_bank=True)
        return obsplus.EventBank(str(paths["bank"]))

    @property
    def events(self) -> pd.DataFrame:
        """Return events DataFrame for this network."""
        paths = resolve_network_paths(self.name, include_events=True)
        return pd.read_parquet(paths["events"])

    @property
    def picks(self) -> pd.DataFrame:
        """Return picks DataFrame for this network."""
        paths = resolve_network_paths(self.name, include_picks=True)
        return pd.read_parquet(paths["picks"])

    @property
    def stations(self) -> pd.DataFrame:
        """Return stations DataFrame for this network."""
        paths = resolve_network_paths(self.name, include_stations=True)
        return pd.read_parquet(paths["stations"])

    def plot_overview(self,savepath=None,
                      stations_type="calculated",
                      show=True):
        """
        Plot network map with events, stations, histograms, and region.

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        stations_type : str
            Column prefix for station coordinates ('calculated' or 'confirmed').
        show : bool
            Whether to display the figure.
        """
        
        stations = self.stations.rename(columns={f"{stations_type}_longitude": "longitude",
                                                f"{stations_type}_latitude": "latitude",
                                                f"{stations_type}_elevation": "elevation"})

        plot_overview(events=self.events, 
                      stations=stations,
                      analysis=self.description,
                      savepath=savepath,
                      show=show)
        
    def plot_stats(self,savepath: str=None,show=True) -> None:
        """
        Create 5-panel seismic overview figure (depth, magnitude, distance, azimuth gap, azimuth distribution).

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """

        plot_stats(self.events, self.picks, savepath=savepath,
                   show=show)
    
    def plot_uncertainty_boxplots(self, savepath: str=None,show=True) -> None:
        """
        Plot horizontal/vertical uncertainty and standard error boxplots.

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """
        plot_uncertainty_boxplots(self.events, savepath=savepath,show=show)

    def plot_pick_stats(self, savepath: str=None,show=True) -> None:
        """
        Plot summary statistics for seismic picks (P, S, S-P).

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """
        plot_pick_stats(self.picks, savepath=savepath, show=show)

    def plot_station_location_uncertainty(self, savepath: str=None, 
                                          show=True) -> None:
        """
        Compare confirmed vs calculated station locations.

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """
        plot_station_location_uncertainty(self.stations, savepath=savepath, 
                                          show=show)

    def plot_pick_histograms(self, savepath: str=None,show=True) -> None:
        """
        Plot histograms of P picks, S picks, and Vp/Vs ratio.

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """
        plot_pick_histograms(self.picks, savepath=savepath,show=show)


    

    
