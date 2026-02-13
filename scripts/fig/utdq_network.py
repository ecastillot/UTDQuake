import os 
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from pathlib import Path
import utdquake as utdq



figs_path = Path(__file__).parent.parent.parent / "figures"
print(f"Saving figure to {figs_path}")

dataset = utdq.Dataset()
network = dataset.get_network("nc")

# network.plot_phase_count_radar_by_magnitude(savepath=figs_path / "t.png")
network.plot_travel_time_vs_distance(savepath=figs_path / "t.png",
                                     distance_unit="degrees")