import os 
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
os.environ["UTDQUAKE_DAS_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

from pathlib import Path
import utdquake as utdq

from utdquake.core.config import get_utdq_paths, get_hf_entry

net_name = "GCI"

# figs_path = Path(__file__).parent.parent.parent / "figures"
figures_path = Path(__file__).parent / "figures"
networks_path = figures_path / "networks_DAS"
net_path = networks_path / net_name
net_path.mkdir(exist_ok=True)
print(f"Saving figure to {figures_path}")

dataset = utdq.Dataset(das=True)
print(dataset)
network = dataset.get_network(net_name)
print(network)

figures_dict = {"overview": figures_path / "utdquake_overview.png",
                "network_overview": networks_path/"{network}"/ "{network}_overview.png",
                "stats": networks_path/"{network}"/ "{network}_stats.png",
                "pick_histograms": networks_path/"{network}"/ "{network}_pick_histograms.png",
                "epi_pick_stats": networks_path/"{network}"/ "{network}_epi_pick_stats.png",
                "hyp_pick_stats": networks_path/"{network}"/ "{network}_hyp_pick_stats.png",
                "phase_count_radar": networks_path/"{network}"/ "{network}_phase_count_radar.png",
                "station_location_uncertainty": networks_path/"{network}"/ "{network}_station_location_uncertainty.png",
                "uncertainty_boxplots": networks_path/"{network}"/ "{network}_uncertainty_boxplots.png",
                "travel_time_qc": networks_path/"{network}"/ "{network}_travel_time_qc.png",
                "travel_time_vs_distance": networks_path/"{network}"/ "{network}_travel_time_vs_distance",
                "travel_time_vs_distance_P_zscore": networks_path/"{network}"/ "{network}_travel_time_vs_distance_P_zscore",
                "travel_time_vs_distance_S_zscore": networks_path/"{network}"/ "{network}_travel_time_vs_distance_S_zscore",
                }


network.plot_overview(savepath=str(figures_dict["network_overview"]).format(network=net_name),
                                is_alaska=True if net_name in ["av", "ak","AEIC"] else False)
network.plot_stats(savepath=str(figures_dict["stats"]).format(network=net_name))
network.plot_pick_histograms(savepath=str(figures_dict["pick_histograms"]).format(network=net_name))
network.plot_phase_count_radar_by_magnitude(savepath=str(figures_dict["phase_count_radar"]).format(network=net_name))
network.plot_pick_stats(distance_type="epicentral",savepath=str(figures_dict["epi_pick_stats"]).format(network=net_name))
network.plot_pick_stats(distance_type="hypocentral",savepath=str(figures_dict["hyp_pick_stats"]).format(network=net_name))
network.plot_station_location_uncertainty(savepath=str(figures_dict["station_location_uncertainty"]).format(network=net_name))
network.plot_uncertainty_boxplots(savepath=str(figures_dict["uncertainty_boxplots"]).format(network=net_name))
network.plot_travel_time_vs_distance(
                                savepath=str(figures_dict["travel_time_vs_distance"]).format(network=net_name),
                                    distance_unit="km")
network.plot_travel_time_vs_distance_zscore(phase="P",
                                savepath=str(figures_dict["travel_time_vs_distance_P_zscore"]).format(network=net_name),
                                )
network.plot_travel_time_vs_distance_zscore(phase="S",
                                savepath=str(figures_dict["travel_time_vs_distance_S_zscore"]).format(network=net_name),
                                )
network.plot_travel_time_qc(savepath=str(figures_dict["travel_time_qc"]).format(network=net_name),
                            show_models=["travel_time_p50"],show_global_model=False,
                            zscore_threshold=3
                            )