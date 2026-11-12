"""Figures of the docs and README (figures/: only what they show), from the local copy of each dataset version. The drawing is in the package:
``Dataset.plot_global_overview`` (utdquake.utils.plot.plot_global_overview), ``Dataset.plot_stats``,
``Dataset.plot_network_station_density``; the paper figures are made by paper/utdq_figures.sh (paper/v1, paper/v2).

    python overview_figures.py latest    # figures/utdquake_overview_stats.png (maps + 5 stats panels: README, home
                                         #   page, index), from the current data (main)
    python overview_figures.py versions  # figures/utdquake_overview_stats_<version>.png (versions page), from
                                         #   paper/<v>/utdq_overview_stats.png (run paper/utdq_figures.sh first)
    python overview_figures.py gif       # figures/all_networks_overview.gif (the networks' overview figures)
"""
import os
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
OUT = HERE / "figures"
PAPER = HERE / "paper"
CURRENT = Path("/groups/igonin/ecastillo/UTDQuake_v2")        # main: v2.0 and the corrections of v2.1
#: versions page: dataset version -> folder of its paper figures
VERSIONS = {"v1.0": "v1", "v2.0": "v2"}


def dataset(root: Path):
    """A Dataset reading the local tables of ``root`` (not the Hub nor its download cache)."""
    os.environ["UTDQUAKE_ROOT"] = str(root)
    os.environ["HF_HUB_OFFLINE"] = "1"
    import pandas as pd
    from utdquake.core.config import get_hf_entry
    from utdquake.core.utdquake import Dataset

    def read(self, key):
        nets = self.local_networks["utdq_net"]
        path = str(root / get_hf_entry(key).path)
        return pd.concat([pd.read_parquet(path.format(utdq_net=n)) for n in nets], ignore_index=True)

    Dataset.networks = property(lambda self: self.local_networks)
    Dataset.events = property(lambda self: read(self, "events"))
    Dataset.stations = property(lambda self: read(self, "stations"))
    return Dataset()


def latest():
    ds = dataset(CURRENT)
    ds.plot_global_overview(layout="combined", savepath=OUT / "utdquake_overview_stats.png")


def versions():
    for version, folder in VERSIONS.items():
        src = PAPER / folder / "utdq_overview_stats.png"
        shutil.copy2(src, OUT / f"utdquake_overview_stats_{version}.png")
        print(f"{version}: {src} -> {OUT / f'utdquake_overview_stats_{version}.png'}")


def gif(fps: float = 0.7, max_frames: int = 50):
    """The networks' overview figures (current data) as one looping GIF, as test/scripts/fig/test_figs_overview.py."""
    import imageio.v2 as imageio
    from PIL import Image
    folder = CURRENT / "figures" / "networks"
    first = ["av", "nc", "ci", "uu", "nm", "ok", "tx", "R03", "R11", "MEX", "hv", "CATAC", "pr", "RSNC", "FUNV",
             "VAO", "SJA", "PRE", "ISK", "INMG", "LDG", "AFAD", "NOA", "ATH", "BEO", "JMA", "DJA", "TAP", "R09",
             "R10", "R01"]
    images = {p.parent.name: p for p in folder.glob("*/*_overview.png")}
    order = ([n for n in first if n in images] + sorted(n for n in images if n not in first))[:max_frames]
    size = max((Image.open(images[n]).size for n in order), key=lambda s: s[0] * s[1])
    frames = [np.array(Image.open(images[n]).convert("RGB").resize(size, Image.Resampling.LANCZOS)) for n in order]
    path = OUT / "all_networks_overview.gif"
    imageio.mimsave(path, frames, duration=1000 / fps, loop=0)
    print(f"gif: {len(frames)} frames {size} -> {path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    {"latest": latest, "versions": versions, "gif": gif}[sys.argv[1]]()
