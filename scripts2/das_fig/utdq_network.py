import os 
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
os.environ["UTDQUAKE_DAS_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

from pathlib import Path
import utdquake as utdq

from utdquake.core.config import get_utdq_paths, get_hf_entry


# figs_path = Path(__file__).parent.parent.parent / "figures"
figs_path = Path(__file__).parent / "figures"
figs_path.mkdir(exist_ok=True)
print(f"Saving figure to {figs_path}")

dataset = utdq.Dataset(das=True)
print(dataset)
network = dataset.get_network("GCI")
print(network)
# network.plot_phase_count_radar_by_magnitude(savepath=figs_path / "magnitude_radar.png")
# network.plot_travel_time_vs_distance(savepath=figs_path / "travel_time.png",
#                                      distance_unit="km")
# network.plot_pick_histograms(savepath=figs_path / "GCI_histogram.png",)
network.plot_overview(savepath=figs_path / "GCI_overview.png",)
# network.plot_pick_stats(distance_type="epicentral",
#                 savepath=figs_path / "GCI_epi_pick_stats.png")
# network.plot_pick_stats(distance_type="hypocentral",
#                 savepath=figs_path / "GCI_hyp_pick_stats.png")
# network.plot_stats(savepath=figs_path / "GCI_stats.png")