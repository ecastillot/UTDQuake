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

    def __init__(self):
        self.root = get_root()

    def __str__(self) -> str:
        return f"UTDQuake(root={self.root})"

    @property
    def description(self) -> str:
        return get_network_summary(stations=self.stations, 
                                    events= self.events)

    @property
    def networks(self):
        return load(key="networks",network="*").to_pandas()

    @property
    def stations(self):
        return load(key="stations",network="*").to_pandas()
    
    @property
    def events(self):
        return load(key="events",network="*").to_pandas()
    
    def get_events(self,network="*",streaming=False,**kwargs):
        return load(key="networks",network=network,
                    streaming=streaming,**kwargs)
    
    def get_stations(self,network="*", streaming: bool=False,
                     **kwargs):
        return load(key="stations",network=network,
                    streaming=streaming,**kwargs)
    
    def get_picks(self,network="*", streaming: bool=True):
        return load(key="picks",network=network,
                    streaming=streaming)
    
    def get_local_networks(self, force_download: bool=False) -> pd.DataFrame:
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
        return Network(name)
    
    def plot_overview(self, savepath=None, show=True):
        """
        Plot a comprehensive UTDQuake overview including events, stations, and analysis.
        """
        plot_utdq_overview(events=self.events,
                            stations=self.stations,
                            analysis=self.description,
                            savepath=savepath,
                            show=show)

class Network:

    def __init__(self, name: str):
        self.name = name.strip() 

    def __str__(self, extended: bool = False) -> str:
        """Return a string representation of the network.

        Parameters
        ----------
        extended : bool
            If True, show all available details. If False, show a summary.
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
        networks_df = Dataset().get_local_networks(force_download=False)
        # networks_df = Dataset().networks.to_pandas()
        network_row = networks_df[networks_df["network"] == self.name]
        if network_row.empty:
            return f"Network '{self.name}' not found."
        network_series = network_row.iloc[0]
        return network_series.to_dict()

    @property
    def bank(self) -> obsplus.EventBank:
        paths = resolve_network_paths(self.name, include_bank=True)
        return obsplus.EventBank(str(paths["bank"]))

    @property
    def events(self) -> pd.DataFrame:
        paths = resolve_network_paths(self.name, include_events=True)
        return pd.read_parquet(paths["events"])

    @property
    def picks(self) -> pd.DataFrame:
        paths = resolve_network_paths(self.name, include_picks=True)
        return pd.read_parquet(paths["picks"])

    @property
    def stations(self) -> pd.DataFrame:
        paths = resolve_network_paths(self.name, include_stations=True)
        return pd.read_parquet(paths["stations"])

    def plot_overview(self,savepath=None,
                      stations_type="calculated",
                      show=True):
        """
        Plot a network map with events, stations, histograms, globe, and region.

        Parameters
        ----------
        savepath : str or None
            If given, save the figure to this path instead of showing it.
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
        Create a 5-panel seismic overview figure:
            - Depth histogram
            - Magnitude histogram
            - Epicentral distance distribution (requires picks)
            - Azimuthal gap (from events)
            - Azimuth distribution (requires picks)
        
        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """

        plot_stats(self.events, self.picks, savepath=savepath,
                   show=show)
    
    def plot_uncertainty_boxplots(self, savepath: str=None,show=True) -> None:
        """
        Create a figure with two axes:
        1. Boxplots for Horizontal and Vertical uncertainty (km)
        2. Boxplot for Standard error

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        plot_uncertainty_boxplots(self.events, savepath=savepath,show=show)

    def plot_pick_stats(self, savepath: str=None,show=True) -> None:
        """
        Plot summary statistics for seismic picks (P, S, and S-P) as jointplots.

        This function computes:
        - First/last P travel times per event
        - First/last S travel times per event
        - First/last S-P times for stations that have both P and S picks
        - Corresponding epicentral distances (converted to km)

        It creates individual seaborn jointplots (scatter + marginal histograms),
        saves them temporarily as PNGs, and then combines them into a single
        multi-panel matplotlib figure.

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        plot_pick_stats(self.picks, savepath=savepath, show=show)

    def plot_station_location_uncertainty(self, savepath: str=None, 
                                          show=True) -> None:
        """
        Compare confirmed vs calculated latitude and longitude in a DataFrame.

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        plot_station_location_uncertainty(self.stations, savepath=savepath, 
                                          show=show)

    def plot_pick_histograms(self, savepath: str=None,show=True) -> None:
        """
        Plots three histograms:
        1. Number of P picks per origin
        2. Number of S picks per origin
        3. Vp/Vs ratio histogram using Wadati method

        Parameters
        ----------
        save_path : str or None
            If given, save the figure to this path instead of showing it.
        """
        plot_pick_histograms(self.picks, savepath=savepath,show=show)


    

    
