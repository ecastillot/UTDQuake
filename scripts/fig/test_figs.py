import os 

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
# os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/bck_utdq/test_021926"

from PIL import Image
from pathlib import Path
import utdquake as utdq
import numpy as np
import datetime
import imageio.v2 as imageio

def create_gif_from_folder(folder: Path, net_name: str, gif_name: str = None, fps: int = 1,
                           ordered_files: list = None):
    """
    Create a looping GIF using images in the exact plotting order.
    Handles the special _map.png case.
    """

    if gif_name is None:
        gif_name = f"{net_name}_summary.gif"

    gif_path = folder / gif_name

    # Explicit order matching your plotting calls
    if ordered_files is None:
        ordered_files = [
            f"{net_name}_overview.png",
            f"{net_name}_stats.png",
            f"{net_name}_histograms.png",
            f"{net_name}_pick_stats.png",
            f"{net_name}_station_location_uncertainty.png",
            # f"{net_name}_station_location_uncertainty_map.png",   # extra figure
            f"{net_name}_uncertainty_boxplots.png",
            f"{net_name}_travel_time_qc.png",  
        ]

    images = [folder / f for f in ordered_files if (folder / f).exists()]
    if not images:
        print(f"No images found in {folder}, skipping GIF creation.")
        return

    # Determine max resolution for best quality
    sizes = [Image.open(img).size for img in images]
    max_width = max(s[0] for s in sizes)
    max_height = max(s[1] for s in sizes)

    target_size = (max_width, max_height)

    frames = []

    for img_path in images:
        img = Image.open(img_path)

        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)

        frames.append(np.array(img))

    # loop=0 → infinite looping GIF
    imageio.mimsave(gif_path, frames, fps=fps, loop=0)

    print(f"Looping GIF created: {gif_path}")



print(f"Script started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

figures_path = Path(__file__).parent.parent.parent / "figures"
print(f"Saving figures to {figures_path}")
networks_path = figures_path / "networks"
os.makedirs(networks_path, exist_ok=True)

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


dataset = utdq.Dataset()
print(dataset)

# network level
network_data = dataset.networks
network_names = network_data["network"].tolist()
# network_names = ["tx"]
# network_names = ["uw","ak","RSNC","tx"]

# dataset.plot_overview(savepath=figures_dict["overview"])
# print(f"Plotted dataset overview to {figures_dict['overview']}")
# print(network_names)
# exit()

for net_name in network_names:
    net_folder = networks_path / net_name
    print(f"Processing network: {net_name} in folder {net_folder}")
    os.makedirs(net_folder, exist_ok=True)

    try:
        # load network 
        network = dataset.get_network(name=net_name)

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

        # ---- CREATE GIF FOR THIS NETWORK ----
        ordered_files = [ f"{net_name}_{x}.png" for x in list(figures_dict.keys()) ] 
        create_gif_from_folder(net_folder, gif_name=f"0.{net_name}.gif",
                               ordered_files= ordered_files ,
                            net_name=net_name, fps=0.7)


    except Exception as e:
        print(f"Error processing network {net_name}: {e}")

# # events
# events = network.events
# print(events)

# # stations
# stations = network.stations
# print(stations)

# # picks
# picks = network.picks
# print(picks)

# # get event bank
# ebank = network.bank # check obsplus.EventBank for more details
# ev_ids = events["event_id"].iloc[:5].tolist()
# cat = ebank.get_events(event_id=ev_ids)
# print(cat)
# cat2 = ebank.get_events(minmagnitude=4.3)
# print(cat2)
