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

>>> net = ds.get_network("tx")
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
import os
import obsplus
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from .data import download_snapshot,load
from .load import resolve_network_paths
from .config import get_hf_entry, get_root, get_utdq_paths
from ..qc.travel_time import TravelTimeModel
from .utils import merge_network_stats
from ..utils.utils import get_network_summary, human_format
from ..utils.plot import (plot_overview,
                          plot_stats,
                          plot_pick_histograms,
                          plot_pick_stats,
                          plot_station_location_uncertainty,
                          plot_uncertainty_boxplots,
                          plot_utdq_overview,
                          plot_network_station_density,
                          plot_phase_count_radar_by_magnitude,
                          plot_travel_time_vs_distance,
                          plot_travel_time_vs_distance_zscore,
                          plot_travel_time_qc,
                          plot_stats_from_stats
                          )

class Dataset:
    """
    High-level interface for the UTDQuake dataset.

    Provides access to networks, stations, events, and picks.
    Allows plotting and summary analysis of the dataset.

    Parameters
    ----------
    das : bool, optional
        If True, use the DAS cache root environment variable (`UTDQUAKE_DAS_ROOT`).
        Otherwise use the standard cache root (`UTDQUAKE_ROOT`). Default is False.
    """

    def __init__(self, das: bool = False):
        """Initialize Dataset with root cache directory.
        """
        self.das = das
        self.root = get_root(das=das)
        self.stats = None 

    def __str__(self) -> str:
        """Return a simple string representation."""
        if self.das:
            return f"UTDQuake(DAS root={self.root})"
        else:
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
        return load(key="networks", das=self.das, network="*").to_pandas()

    @property
    def local_networks(self):
        """Return all local networks as a Pandas DataFrame."""
        networks_path = self.root / get_hf_entry("networks",self.das).path
        
        if not networks_path.exists():
            raise FileNotFoundError(f"Local networks metadata not found at {networks_path}. Please run download(networks='*',include_networks=True) to fetch the data.")
        return pd.read_parquet(networks_path)

    @property
    def stations(self):
        """Return all stations as a Pandas DataFrame."""
        return load(key="stations", das=self.das,network="*").to_pandas()
    
    @property
    def events(self):
        """Return all events as a Pandas DataFrame."""
        return load(key="events", das=self.das,network="*").to_pandas()

    def get_network(self, name: str):
        """Return a Network object for a given network name."""
        return Network(name,das=self.das)

    def get_events(self,network="*",streaming=False,**kwargs):
        """Return events for a specific network."""
        return load(key="events", das=self.das,network=network,
                    streaming=streaming,**kwargs)
    
    def get_stations(self,network="*", streaming: bool=False,
                     **kwargs):
        """Return stations for a specific network."""
        return load(key="stations", das=self.das,network=network,
                    streaming=streaming,**kwargs)
    
    def get_picks(self,network="*", streaming: bool=True):
        """Return picks for a specific network."""
        return load(key="picks", das=self.das,network=network,
                    streaming=streaming)
    
    def download(self,networks: Union[str, List[str]],
                    include_networks: bool = True,
                    include_events: bool = False,
                    include_stations: bool = False,
                    include_picks: bool = False,
                    include_banks: bool = False,
                    include_travel_time: bool = False,
                    unzip_banks: bool = True,
                    overwrite: bool = False,
                ) -> Path:
        """
        Download selected data from the UTDQuake Hugging Face repository.

        Parameters
        ----------
        networks : str or list of str
            Networks to download:
            - "*" downloads all networks
            - "t*" downloads all networks starting with 't'
            - ["tx", "uw"] downloads only specified networks
        include_networks : bool, optional
            Whether to download the network metadata. Default: True.
        include_events : bool, optional
            Whether to download the events data. Default: False.
        include_stations : bool, optional
            Whether to download station metadata. Default: False.
        include_picks : bool, optional
            Whether to download seismic picks. Default: False.
        include_banks : bool, optional
            Whether to download the bank (synthetic) data. Default: False.
        include_travel_time : bool, optional
            Whether to download the travel time models. Default: False.
        overwrite : bool, optional
            If True, existing files will be re-downloaded. Default: False.
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
        >>> download(networks=["tx", "uw"], include_picks=True, overwrite=False)
        """
        return download_snapshot(
            local_dir=self.root,
            networks=networks,
            das=self.das,
            include_networks=include_networks,
            include_events=include_events,
            include_stations=include_stations,
            include_picks=include_picks,
            include_banks=include_banks,
            include_travel_time=include_travel_time,
            overwrite=overwrite,
            unzip_banks=unzip_banks
        )

    def compute_stats(self, networks: Optional[List[str]] = None, 
                  use_cache=True, distance_bins=None,
                  merge=False) -> dict:
        """
        Compute statistics for multiple networks and cache results.

        Parameters
        ----------
        networks : list of str, optional
            List of network names. If None or '*', use all local networks.
        use_cache : bool
            Whether to use cached stats if available.
        distance_bins : list, optional
            Distance bins for epicentral distance histograms.
        merge : bool
            If True, merge stats across networks for combined analysis. Default: False.

        Returns
        -------
        all_stats : dict
            If merge=False: {network_name: stats_dict}  
            If merge=True: single merged stats_dict suitable for plotting
        """
        all_stats = {}
        net_names = self.networks["network"].tolist() if networks == "*" \
                    or networks is None else networks

        for name in net_names:
            net = self.get_network(name)
            stats = net.compute_stats(use_cache=use_cache, distance_bins=distance_bins)
            all_stats[name] = stats
        if merge:
            merged_stats = merge_network_stats(all_stats, distance_bins=distance_bins)
            self.stats = merged_stats
            return merged_stats
        else:
            self.stats = all_stats
            return all_stats

    def plot_stats(self,savepath=None, show=True):
        """
        Plot a 5-panel figure using precomputed network stats.
        See `Network.compute_stats(merge=True)` for expected stats structure.
        
        Panels: depth, magnitude, epicentral distance, azimuthal gap, azimuth distribution.

        Parameters
        ----------
        savepath : str, optional
            Path to save the figure. Default: None.
        show : bool, optional
            If True, display the figure. Default: True.

        """
        # if is a dict of dicts, raise error
        if isinstance(self.stats, dict) and all(isinstance(v, dict) for v in self.stats.values()):
            raise ValueError("Stats appear to be unmerged. Please run compute_stats(merge=True) before plotting.")

        plot_stats_from_stats(self.stats, savepath=savepath, show=show)

    def plot_travel_time(self, networks: str=None,
                        zscore_threshold: str=3, 
                        savepath: str=None, 
                        show=True):

        net_names = self.networks["network"].tolist() if networks == "*" \
                    or networks is None else networks

        fig, axes = plt.subplots(2, 3, figsize=(12, 8))
        axes = axes.flatten()
        axins = [ inset_axes(ax, width="35%", 
                    height="35%", loc="upper left") \
                        for ax in axes]
        
        legend_args = None
        for name in net_names:
            net = self.get_network(name)

            model_path = net.paths["utdq/travel_time"]

            if not model_path.exists():
                raise FileNotFoundError(f"Travel time model not found for network {name} at {model_path}.")

            load = TravelTimeModel.load(model_path)
            models = load.models

            picks = net.picks
            picks = picks[picks["travel_time_zscore"] < zscore_threshold]
            _,_,_,l_args = plot_travel_time_qc(
                            df=net.picks,
                            models=models,
                            zscore_threshold=zscore_threshold,
                            axes=axes,     
                            axins=axins,         
                            add_inset=True,  
                            show_outliers=False,      
                            show_text=False,        
                            show_models=None,
                            turn_off_empty_axes=False,
                            show_legend=False,
                            x_limits=(0, None),
                            y_limits=(0, None),
                            x_axins_limits = (0, 150),
                            y_axins_limits = (0, 30),
                            scatter_args={"alpha": 0.3, "s": 1, 
                                            "edgecolors": "none"}        
                        )
            if legend_args is None:
                legend_args = l_args

        legend_handles, legend_labels = legend_args
        for handle in legend_handles:
            if hasattr(handle, "set_alpha"):
                handle.set_alpha(1)  # full opacity for markers
        fig.legend(
            legend_handles, legend_labels,
            loc='lower center',
            bbox_to_anchor=(0.5, -0.05),
            ncol=len(legend_labels),
            markerscale=8,
            frameon=True,
            
            prop={'size': 12}
        )

        if savepath:
            fig.savefig(savepath, dpi=300, bbox_inches='tight')
            print(f"Saved figure to {savepath}")
        
        if show:
            plt.show()
            plt.close(fig)

    def plot_overview(self, consider_calculated_stations: bool=True,
                    savepath=None, show=True):
        """
        Plot a comprehensive overview of UTDQuake dataset.

        Includes events, stations, and summary analysis.

        Parameters
        ----------
        consider_calculated_stations : bool, optional
            If True, also plot calculated stations (if available). Defaults to True.
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """
        plot_utdq_overview(events=self.events,
                            stations=self.stations,
                            analysis=self.description,
                            das=self.das,
                            savepath=savepath,
                            consider_calculated_stations=consider_calculated_stations,
                            show=show)

    def plot_network_station_density(self, density_in_region:bool=True, savepath: str=None, show=True):
        """
        Plot station density maps for all networks.

        Parameters:
        ----------
        density_in_region : bool, optional
            If True, calculate station density only within the network's defined region. Default is True.
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """
        if density_in_region:
            print("Calculating station density within network regions...")
            networks = self.networks.copy()
            stations = self.stations.copy()

            confirmed_mask = stations["confirmed"] == True
            only_calculated_mask = (stations["confirmed"] == False) & (stations["available"] == True)
            stations = stations[confirmed_mask | only_calculated_mask]
            stations["latitude"] = stations["confirmed_latitude"].combine_first(stations["calculated_latitude"])
            stations["longitude"] = stations["confirmed_longitude"].combine_first(stations["calculated_longitude"])

            networks_reg = networks[["network","approx_lon_min",	"approx_lon_max",	"approx_lat_min",	"approx_lat_max"]]
            n_stations = pd.merge(stations, networks_reg, on="network", how="left")
            n_stations = n_stations[(n_stations["latitude"] >= n_stations["approx_lat_min"]) & (n_stations["latitude"] <= n_stations["approx_lat_max"])]
            n_stations = n_stations[(n_stations["longitude"] >= n_stations["approx_lon_min"]) & (n_stations["longitude"] <= n_stations["approx_lon_max"])]
            counts = n_stations["network"].value_counts().to_dict()
            networks["total_stations"] = networks.apply(lambda row: counts.get(row["network"], np.nan), axis=1)
        
            # #in case of polygon area / no need for now, but leaving here for future reference
            # gdf = gpd.GeoDataFrame(
            #     n_stations,
            #     geometry=gpd.points_from_xy(n_stations.longitude, n_stations.latitude),
            #     crs="EPSG:4326"
            # )
            # def area_deg2(group):
            #     if len(group) < 3:
            #         return 0.0
            #     hull = group.geometry.union_all().convex_hull
            #     return hull.area  # degree^2

            # area_per_network = (
            #     gdf.groupby("network")
            #     .apply(area_deg2)
            #     .reset_index(name="area_deg2")
            #         )
            # area_per_network = area_per_network.set_index("network")["area_deg2"].to_dict()
            # networks["area_deg2"] = networks.apply(lambda row: area_per_network.get(row["network"], np.nan), axis=1)
        
        else:
            networks = self.networks.copy()

        plot_network_station_density(networks, 
                                savepath=savepath, show=show)
        
    def plot_phase_count_radar_by_magnitude(self, savepath: str=None, show=True):
        """
        Create radar plots of phase and station counts binned by magnitude.

        For each magnitude range, the function displays the mean values of
        P phases, S phases, used phases, and station counts in a radar chart.
        Variability is represented using interquartile range (IQR) and the
        10–90 percentile envelope.

        Parameters:
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        """
        plot_phase_count_radar_by_magnitude(self.events,
                                            savepath=savepath,
                                            show=show)

    def plot_travel_time_vs_distance(self, 
                                     distance_unit="degrees",log_scale=False,
                                     savepath: str=None, show=True
                                     ):
        """
        Plot travel time versus distance for seismic picks.

        Creates a scatter plot of travel time (y-axis) against distance (x-axis),
        with points colored by seismic phase type.
        
        Parameters:
        ----------
        distance_unit : str, optional
            Unit for the x-axis distance. Options are:
            - "degrees" (default)
            - "km"

            If "km" is selected, the distance in degrees is converted
            to kilometers using an approximate Earth conversion
            (1 degree ≈ 111.19 km).

        log_scale : bool, optional
            Whether to use logarithmic scale on the x-axis
            (default is False).

        show : bool, optional
            Whether to display the plot on screen (default is True).

        savepath : str or None, optional
            If provided, the figure will be saved to this path with
            dpi=300 (default is None).
        """
        picks = self.get_picks(network="*", streaming=False).to_pandas()
        picks = picks[picks["travel_time"] > 0]  # Filter out non-positive travel times
        picks["travel_time"] = picks["travel_time"] / 60  # Convert to minutes
        picks = picks[picks["travel_time"] < 100]  # Filter out non-positive travel times
        plot_travel_time_vs_distance(picks, distance_unit=distance_unit,
                                        log_scale=log_scale, savepath=savepath,
                                        show=show)

class Network:
    """
    Represents a single network in UTDQuake.

    Provides access to network-specific events, stations, picks,
    EventBank, and plotting utilities.

    Parameters
    ----------
    name : str
        Network name (e.g. "tx", "uw", "GCI").
    das : bool, optional
        Whether to use the DAS or not. If so, tou may define DAS cache root environment variable (`UTDQUAKE_DAS_ROOT`).
    """

    def __init__(self, name: str, das: bool = False):
        """Initialize Network with name and DAS flag."""
        self.name = name.strip() 
        self.das = das
        self.paths = get_utdq_paths(name,das)

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

        das_str = "DAS: " if self.das else ""
        msg = f"Network({das_str}{self.name})"

        if not extended:
            events = description.get("events", "N/A")
            stations = description.get("total_stations", "N/A")
            msg += f" | Events: {events}, Stations: {stations}"
            if self.das:
                channels = description.get("total_channels", "N/A")
                msg += f", Channels: {human_format(channels)}"

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
        # networks_df =  Dataset(self.das).local_networks
        networks_df = Dataset(das=self.das).networks
        # print(networks_df)

        network_row = networks_df[networks_df["network"] == self.name]
        if network_row.empty:
            raise Exception(f"Network '{self.name}' not found.") 
        network_series = network_row.iloc[0]
        return network_series.to_dict()

    @property
    def bank(self) -> obsplus.EventBank:
        """Return the ObsPlus EventBank for this network."""
        paths = resolve_network_paths(self.name,das=self.das, include_bank=True)
        return obsplus.EventBank(str(paths["bank"]))

    @property
    def events(self) -> pd.DataFrame:
        """Return events DataFrame for this network."""
        paths = resolve_network_paths(self.name,das=self.das, include_events=True)
        return pd.read_parquet(paths["events"])

    @property
    def picks(self) -> pd.DataFrame:
        """Return picks DataFrame for this network."""
        paths = resolve_network_paths(self.name,das=self.das, include_picks=True)
        return pd.read_parquet(paths["picks"])

    @property
    def stations(self) -> pd.DataFrame:
        """Return stations DataFrame for this network."""
        paths = resolve_network_paths(self.name,das=self.das, include_stations=True)
        return pd.read_parquet(paths["stations"])

    @property
    def travel_time(self) -> TravelTimeModel:
        """Return the TravelTimeModel for this network."""
        paths = resolve_network_paths(self.name,das=self.das, include_travel_time=True)
        return TravelTimeModel.load(paths["travel_time"])

    def compute_stats(
                    self,
                    use_cache=True,
                    distance_bins: list = None
                ) -> dict:
        """
        Compute basic statistics for this network and cache results.

        Parameters
        ----------
        use_cache : bool
            If True, load cached stats if available.
        distance_column : str
            Column in picks to use for distance calculation. Can be 'distance' (deg) or 'hyp_linear_distance' (km).
        distance_bins : list, optional
            Bin edges for epicentral distance histogram. Default: [0,30,60,100,150,200,300,np.inf].

        Returns
        -------
        stats : dict
            Dictionary with computed stats:
            - depth_values
            - magnitude_values, mag_min, mag_max
            - distance_bins, counts_P, counts_S
            - az_gap_hist
            - azimuth_hist
        """
        cache_file = self.paths[".utdquake/stats"]

        if use_cache and os.path.exists(cache_file):
            data = np.load(cache_file, allow_pickle=True)
            stats = {k: data[k] for k in data.files}
            print(f"{self.name} stats loaded from cache: {cache_file}")
            return stats

        # Default distance bins
        if distance_bins is None:
            distance_bins = [0, 30, 60, 100, 150, 200, 300,500, np.inf]

        # Load events & picks
        events = self.events
        picks = self.picks 

        stats = {}

        # --- Depth & magnitude ---
        stats["depth_values"] = (events["depth"].dropna() / 1e3).values
        stats["magnitude_values"] = events["magnitude"].dropna().values

        # --- Epicentral distance (picks-dependent) ---
        picks["distance_km"] = picks["distance"] * 111

        p_picks = picks[picks["phase"] == "P"]
        s_picks = picks[picks["phase"] == "S"]

        epi_counts_P, _ = np.histogram(p_picks["distance_km"], bins=distance_bins)
        epi_counts_S, _ = np.histogram(s_picks["distance_km"], bins=distance_bins)
        hyp_counts_P, _ = np.histogram(p_picks["linear_hyp_distance"], bins=distance_bins)
        hyp_counts_S, _ = np.histogram(s_picks["linear_hyp_distance"], bins=distance_bins)

        stats["distance_bins"] = distance_bins
        stats["epi_dist_counts_P"] = epi_counts_P
        stats["epi_dist_counts_S"] = epi_counts_S
        stats["hyp_dist_counts_P"] = hyp_counts_P
        stats["hyp_dist_counts_S"] = hyp_counts_S

        # --- Azimuthal gap ---
        az_gap = np.deg2rad(events["azimuthal_gap"].dropna().values)
        counts_gap, bins_gap = np.histogram(az_gap, bins=12, range=(0, 2*np.pi))
        # stats["az_gap_hist"] = (counts_gap, bins_gap)
        stats["az_gap_counts"] = counts_gap
        stats["az_gap_bins"] = bins_gap

        # --- Azimuth (from picks) ---
        if picks is not None:
            picks = picks.drop_duplicates(subset=["origin_id", "network", "station"])
            az = np.deg2rad(picks["azimuth"].dropna().values)
            counts_az, bins_az = np.histogram(az, bins=12, range=(0, 2*np.pi))
            # stats["azimuth_hist"] = (counts_az, bins_az)
            stats["azimuth_counts"] = counts_az
            stats["azimuth_bins"] =  bins_az
        else:
            stats["azimuth_counts"] = None
            stats["azimuth_bins"] = None

        # --- Save to cache ---
        np.savez_compressed(
                    cache_file,
                    depth_values=stats["depth_values"],
                    magnitude_values=stats["magnitude_values"],
                    distance_bins=stats["distance_bins"],
                    epi_dist_counts_P=stats["epi_dist_counts_P"],
                    epi_dist_counts_S=stats["epi_dist_counts_S"],
                    hyp_dist_counts_P=stats["hyp_dist_counts_P"],
                    hyp_dist_counts_S=stats["hyp_dist_counts_S"],
                    az_gap_counts=stats["az_gap_counts"],
                    az_gap_bins=stats["az_gap_bins"],
                    azimuth_counts=stats["azimuth_counts"],
                    azimuth_bins=stats["azimuth_bins"],
                )

        return stats


    def plot_overview(self,
                      consider_calculated_stations: bool=True,
                      is_alaska=False,
                      savepath=None,
                      show=True, **kwargs):
        """
        Plot network map with events, stations, histograms, and region.

        Parameters
        ----------
        consider_calculated_stations : bool, optional
            If True, also plot calculated stations (if available). Defaults to True.
        is_alaska : bool, optional
            If True, use a projection suitable for Alaska. Default: True.
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_overview`.

        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_overview`.
        """
        return plot_overview(events=self.events, 
                      stations=self.stations,
                      analysis=self.description,
                      das=self.das,
                      consider_calculated_stations=consider_calculated_stations,
                      is_alaska=is_alaska,
                      savepath=savepath,
                      show=show, **kwargs)
        
    def plot_stats(self,savepath: str=None,show=True, **kwargs) -> None:
        """
        Create 5-panel seismic overview figure (depth, magnitude, distance, azimuth gap, azimuth distribution).

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_stats`.
        
        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_stats`.
        """

        return plot_stats(self.events, self.picks, savepath=savepath,
                   show=show, **kwargs)
    
    def plot_uncertainty_boxplots(self, savepath: str=None,show=True, **kwargs) -> None:
        """
        Plot horizontal/vertical uncertainty and standard error boxplots.

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_uncertainty_boxplots`.

        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_uncertainty_boxplots`.
        """
        return plot_uncertainty_boxplots(self.events, savepath=savepath,show=show,**kwargs)

    def plot_pick_stats(self, distance_type="epicentral", savepath: str=None,
                        show=True, **kwargs) -> None:
        """
        Plot summary statistics for seismic picks (P, S, S-P).

        The function computes:
        - First and last P travel times per event.
        - First and last S travel times per event.
        - First and last S-P times for stations with both P and S picks.
        - Corresponding distances (either epicentral or hypocentral).

        It creates individual seaborn jointplots (scatter + marginal histograms),
        saves them temporarily as PNGs, and combines them into a single multi-panel
        matplotlib figure.

        Parameters
        ----------
        distance_type : str, default "epicentral"
            Which distance to use:
            - "epicentral": horizontal distance from epicenter.
            - "hypocentral": approximate distance from hypocenter (linear approx.).
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_pick_stats`.

        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_pick_stats`.
        """
        return plot_pick_stats(self.picks, distance_type=distance_type, 
                               savepath=savepath, show=show, **kwargs)

    def plot_station_location_uncertainty(self, savepath: str=None, 
                                          show=True,**kwargs) -> None:
        """
        Compare confirmed vs calculated station locations.

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_station_location_uncertainty`.

        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_station_location_uncertainty`.
        """
        return plot_station_location_uncertainty(self.stations, 
                                                 savepath=savepath, 
                                                 show=show,**kwargs)

    def plot_pick_histograms(self, savepath: str=None,show=True,
                                            **kwargs) -> None:
        """
        Plot histograms of P picks, S picks, and Vp/Vs ratio.

        Parameters
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_pick_histograms`.

        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_pick_histograms`.
        """
        return plot_pick_histograms(self.picks, savepath=savepath,show=show,
                                            **kwargs)

    def plot_phase_count_radar_by_magnitude(self, savepath: str=None, show=True,
                                            **kwargs):
        """
        Create radar plots of phase and station counts binned by magnitude.

        For each magnitude range, the function displays the mean values of
        P phases, S phases, used phases, and station counts in a radar chart.
        Variability is represented using interquartile range (IQR) and the
        10–90 percentile envelope.

        Parameters:
        ----------
        savepath : str or None
            Path to save the figure. If None, figure is not saved.
        show : bool
            Whether to display the figure.
        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_phase_count_radar_by_magnitude`.

        Returns:
        -------
        Same as :func:`utdquake.utils.plot.plot_phase_count_radar_by_magnitude`.
        """
        return plot_phase_count_radar_by_magnitude(self.events,
                                            savepath=savepath,
                                            show=show,
                                            **kwargs)
        
    def plot_travel_time_vs_distance(self, 
                                     distance_unit="degrees",log_scale=False,
                                     savepath: str=None, show=True,
                                     **kwargs
                                     ):
        """
        Plot travel time versus distance for seismic picks.

        Creates a scatter plot of travel time (y-axis) against distance (x-axis),
        with points colored by seismic phase type.
        
        Parameters:
        ----------
        distance_unit : str, optional
            Unit for the x-axis distance. Options are:
            - "degrees" (default)
            - "km"

            If "km" is selected, the distance in degrees is converted
            to kilometers using an approximate Earth conversion
            (1 degree ≈ 111.19 km).

        log_scale : bool, optional
            Whether to use logarithmic scale on the x-axis
            (default is False).

        show : bool, optional
            Whether to display the plot on screen (default is True).

        savepath : str or None, optional
            If provided, the figure will be saved to this path with
            dpi=300 (default is None).

        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_travel_time_vs_distance`.
        
        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_travel_time_vs_distance`.

        """
        return plot_travel_time_vs_distance(self.picks, distance_unit=distance_unit,
                                        log_scale=log_scale, savepath=savepath,
                                        show=show,**kwargs)

    def plot_travel_time_vs_distance_zscore(self, 
                                    phase="P",
                                    distance_unit="hypo_km",
                                    savepath: str=None, 
                                    x_lim=(0,300),
                                    y_lim=(0,50),
                                    **kwargs
                                     ):
        """
        Plot travel time versus distance colored by z-score values.

        Parameters
        ----------
        picks : pandas.DataFrame
            Input DataFrame containing seismic pick information.

            Required columns depend on the selected ``distance_unit``:

            Common required columns:

            - ``travel_time``
            - ``phase``
            - ``travel_time_zscore``

            Additional distance column:

            - ``distance`` for ``"degrees"`` or ``"km"``
            - ``linear_hyp_distance`` for ``"hypo_km"``

        phase : str or None, default=None
            Seismic phase to plot. If ``None``, all phases are included.

        distance_unit : str, default="degrees"
            Distance representation used for the x-axis.

            Supported options are:

            - ``"degrees"``
            - ``"km"``
            - ``"hypo_km"``

        log_scale : bool, default=False
            If ``True``, apply logarithmic scaling to the x-axis.

        show : bool, default=True
            If ``True``, display the figure.

        savepath : str or None, default=None
            Output path used to save the generated figure.

        point_size : int, default=5
            Marker size used in scatter plots.

        zmax : float, default=3.0
            Maximum z-score value used for color normalization.

            Picks with absolute z-score values larger than ``zmax`` are
            classified as outliers.

        x_lim : tuple or None, default=None
            X-axis limits in the form ``(xmin, xmax)``.

        y_lim : tuple or None, default=None
            Y-axis limits in the form ``(ymin, ymax)``.

        add_inset : bool, default=True
            If ``True``, add a zoomed inset axis.

        x_axins_limits : tuple, default=(0, 30)
            X-axis limits for the inset axes.

        y_axins_limits : tuple, default=(0, 10)
            Y-axis limits for the inset axes.

        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_travel_time_vs_distance_zscore`.

        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_travel_time_vs_distance_zscore`.
        
        Raises
        ------
        ValueError
            If ``picks`` is not a pandas DataFrame.

        ValueError
            If required columns are missing.

        ValueError
            If no picks are available for the selected phase.

        Notes
        -----
        - Absolute z-score values are used for thresholding.
        - Outliers are plotted in gray.
        - A colorbar indicates z-score magnitude.
        - Approximate conversion factor:
        ``1 degree = 111.19 km``.

        """
        if self.das:
            raise NotImplementedError("Travel time QC plotting is not currently implemented for DAS networks.")
        return plot_travel_time_vs_distance_zscore(self.picks,
                                    phase=phase,
                                    distance_unit=distance_unit,
                                    x_lim=x_lim,
                                    y_lim=y_lim,
                                    savepath=savepath,
                                    **kwargs
                                    )

    def plot_travel_time_qc(self,
               add_inset: bool = True,
               zscore_threshold: float = 2,
               show_text: bool = True,
               show_models: Optional[List[str]] = None,
               show_global_model: bool = False,
               distance_col: str = "linear_hyp_distance",
               tt_col: str = "travel_time",
               x_axins_limits: Tuple[float, float] = (0, 30),
               y_axins_limits: Tuple[float, float] = (0, 10),
               savepath: Optional[str] = None,
               **kwargs
               ):
        """
        Plot multi-phase travel-time QC with optional inset zooms.

        Parameters
        ----------
        df : pd.DataFrame
            Travel-time data with multiple phases.
        add_inset : bool, optional
            Add zoomed inset plots (default: True).
        zscore_threshold : float, optional
            Z-score threshold for outlier detection (default: 2).
        show_text : bool, optional
            Show text annotations on each subplot (default: True).
        show_models : list of str, optional
            Columns in model to plot (default: ["travel_time_p50"]).
        show_global_model : bool, optional
            Display global trend bounds (default: False).
        distance_col : str, optional
            Column name for distance (default: "linear_hyp_distance").
        tt_col : str, optional
            Column name for travel time (default: "travel_time").
        x_axins_limits : tuple, optional
            X-axis limits for inset (default: (0, 30)).
        y_axins_limits : tuple, optional
            Y-axis limits for inset (default: (0, 10)).
        savepath : str, optional
            Path to save figure (default: None).
        **kwargs
            Additional keyword arguments passed directly to
            :func:`utdquake.utils.plot.plot_travel_time_qc`.

        Returns
        -------
        Same as :func:`utdquake.utils.plot.plot_travel_time_qc`.
        """
        if self.das:
            raise NotImplementedError("Travel time QC plotting is not currently implemented for DAS networks.")

        model_path = self.paths[".utdquake/travel_time"]
        
        if not model_path.exists():
            resolve_network_paths(self.name,das=False,
                      include_bank=False,
                      include_events=False,
                        include_stations=False,
                        include_picks=False,
                        include_travel_time=True,
                      )
            
        load = TravelTimeModel.load(model_path)
        models = load.models

        return plot_travel_time_qc(df=self.picks, add_inset=add_inset, zscore_threshold=zscore_threshold,
                            models=models,
                            show_text=show_text, show_models=show_models,
                            show_global_model=show_global_model, distance_col=distance_col,
                            tt_col=tt_col, 
                            x_limits=(0, None), y_limits=(0, None),
                            x_axins_limits=x_axins_limits,
                            y_axins_limits=y_axins_limits, savepath=savepath,
                            **kwargs)
        
