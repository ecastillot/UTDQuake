import os 

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

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


def create_overview_gif(
    folder: Path,
    gif_name: str = "all_networks_overview.gif",
    fps: float = 1.0,
    priority_order: list = None,
    max_figures: int = None
):
    """
    Create a GIF using only *_overview.png images from multiple networks.

    Parameters
    ----------
    folder : Path
        Base folder containing network subfolders.
    gif_name : str
        Name of output gif.
    fps : float
        Frames per second.
    priority_order : list[str], optional
        List of network names that should appear first in the GIF.
        Example: ["TX", "RSNC", "AV"]
    max_figures : int, optional
        If given, only the first N images (after ordering) are used.
    """

    gif_path = folder.parent / gif_name

    # Find all overview images recursively
    images = sorted(folder.rglob("*_overview.png"))

    if not images:
        print(f"No overview images found in {folder}")
        return

    # Map network name → image path
    image_map = {}
    for img in images:
        net_name = img.parent.name
        image_map[net_name] = img

    ordered_images = []

    # 1) Put priority networks first (if provided)
    if priority_order:
        for net in priority_order:
            if net in image_map:
                ordered_images.append(image_map.pop(net))

    # 2) Append the rest in alphabetical order
    for net in sorted(image_map.keys()):
        ordered_images.append(image_map[net])

    # 3) Limit number of figures if requested
    if max_figures is not None:
        ordered_images = ordered_images[:max_figures]

    print(f"Creating GIF from {len(ordered_images)} images")

    # Determine maximum size
    sizes = [Image.open(img).size for img in ordered_images]
    max_width = max(s[0] for s in sizes)
    max_height = max(s[1] for s in sizes)

    target_size = (max_width, max_height)

    frames = []

    for img_path in ordered_images:
        img = Image.open(img_path)

        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)

        frames.append(np.array(img))

    imageio.mimsave(gif_path, frames, fps=fps, loop=0)

    print(f"Overview GIF created: {gif_path}")



# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

print(f"Script started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
figures_path = Path(__file__).parent.parent.parent / "figures"
print(f"Saving figures to {figures_path}")

networks_path = figures_path / "networks"
create_overview_gif(
    networks_path,
    priority_order=["av","nc","uu","nm","ok","tx","MEX","hv","CATAC","pr",
                    "RSNC","FUNV", "VAO", "SJA",
                    "PRE","EAF","ISK","INMG"
                    "LDG","AFAD","NOA","ATH","BEO",
                    "JAPAN","DJA","TAP"
                    ],
    max_figures=50,
    fps=0.7
)