import os
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from pathlib import Path
import utdquake as utdq

fig_path = Path(__file__).parent / "utdq_magnitude.png"
print(f"Saving figure to {fig_path}")

dataset = utdq.Dataset()
network_data = dataset.networks
network_names = network_data["network"].tolist()

# network_names = ["RSNC"]

dataset = utdq.Dataset()

dataset.plot_phase_count_radar_by_magnitude(savepath=fig_path)


