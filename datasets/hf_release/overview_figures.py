"""Overview figures of the docs (README, home page, versions page), from the local copy of each dataset version.

    python overview_figures.py maps     # figures/utdquake_overview_<version>.png (+ utdquake_overview.png = latest)
    python overview_figures.py gif      # figures/all_networks_overview.gif (the networks' overview figures)

Maps: earthquakes and stations of every seismic UTDQuake network of the version (DAS not included), Robinson
projection; station counts are distinct (network, station) pairs, as Dataset.description.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[2]
OUT = HERE / "figures"
VERSIONS = {   # version -> local root holding exactly that version
    "v1.0": Path("/groups/igonin/ecastillo/UTDQuake_paper_v1"),
    "v2.0": Path("/groups/igonin/ecastillo/UTDQuake_v2"),
}
LATEST = "v2.0"
EVENT_COLOR, CONF_COLOR, CALC_COLOR = "#E87500", "#1b7a3a", "#8a8a8a"


def load(root: Path):
    table = pd.read_parquet(root / "network" / "network.parquet")
    nets = sorted(table["utdq_net"].astype(str))
    ev = pd.concat([pd.read_parquet(root / f"events/utdq_net={n}.parquet", columns=["latitude", "longitude"])
                    for n in nets], ignore_index=True)
    st = pd.concat([pd.read_parquet(root / f"stations/utdq_net={n}.parquet") for n in nets], ignore_index=True)
    st = st.sort_values("confirmed", ascending=False, na_position="last").drop_duplicates(["network", "station"])
    conf = st["confirmed"].fillna(False).astype(bool) & st["confirmed_latitude"].notna()
    calc = ~conf & st["calculated_latitude"].notna()
    from utdquake.utils.utils import get_network_summary
    evs = pd.concat([pd.read_parquet(root / f"events/utdq_net={n}.parquet",
                                     columns=["latitude", "longitude", "time", "p_phase_count", "s_phase_count"])
                     for n in nets], ignore_index=True)
    allst = pd.concat([pd.read_parquet(root / f"stations/utdq_net={n}.parquet") for n in nets], ignore_index=True)
    summary = get_network_summary(stations=allst, events=evs, distinct_stations=True)
    pick_cols = ["phase"]
    p_n = s_n = 0
    for n in nets:
        ph = pd.read_parquet(root / f"picks/utdq_net={n}.parquet", columns=pick_cols)["phase"].astype(str).str.upper()
        p_n += int(ph.str.startswith("P").sum())
        s_n += int(ph.str.startswith("S").sum())
    return {"networks": len(nets), "events": ev.dropna(), "p": p_n, "s": s_n,
            "stations": int(summary["total_stations"]), "located": int(summary["located_stations"]),
            "confirmed": int(summary["confirmed_stations"]),
            "conf_xy": st.loc[conf, ["confirmed_longitude", "confirmed_latitude"]].to_numpy(),
            "calc_xy": st.loc[calc, ["calculated_longitude", "calculated_latitude"]].to_numpy()}


def human(x: float) -> str:
    return f"{x / 1e6:.1f} M" if x >= 1e6 else f"{x / 1e3:.1f} K" if x >= 1e3 else str(x)


def draw(version: str, d: dict, path: Path) -> None:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    proj = ccrs.Robinson(central_longitude=0)
    fig = plt.figure(figsize=(12, 13.2), dpi=200)
    # legend (title and counts) above each map
    axes = [fig.add_axes([0.02, 0.47, 0.96, 0.40], projection=proj),
            fig.add_axes([0.02, 0.01, 0.96, 0.40], projection=proj)]
    for ax in axes:
        ax.set_global()
        ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor="#ececec", edgecolor="#9a9a9a", linewidth=0.4)
        ax.add_feature(cfeature.OCEAN.with_scale("110m"), facecolor="white")
        ax.spines["geo"].set_linewidth(1.2)
    ev = d["events"]
    axes[0].scatter(ev["longitude"], ev["latitude"], s=1.4, c=EVENT_COLOR, alpha=0.55, linewidths=0,
                    transform=ccrs.PlateCarree(), rasterized=True)
    if len(d["calc_xy"]):
        axes[1].scatter(d["calc_xy"][:, 0], d["calc_xy"][:, 1], s=7, marker="^", c=CALC_COLOR, alpha=0.7,
                        linewidths=0, transform=ccrs.PlateCarree(), rasterized=True)
    axes[1].scatter(d["conf_xy"][:, 0], d["conf_xy"][:, 1], s=7, marker="^", c=CONF_COLOR, alpha=0.8,
                    linewidths=0, transform=ccrs.PlateCarree(), rasterized=True)
    fig.suptitle(f"UTDQuake {version}: {d['networks']} networks",
                 fontsize=19, y=0.975)
    fs = 14
    blank = Line2D([], [], ls="", marker="")
    leg = axes[0].legend(handles=[Line2D([], [], marker="o", ls="", color=EVENT_COLOR, ms=9), blank, blank],
                         labels=[f"{human(len(ev))} earthquakes", f"P picks: {human(d['p'])}",
                                 f"S picks: {human(d['s'])}"],
                         title="Earthquakes", loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
                         frameon=False, fontsize=fs, title_fontproperties={"weight": "bold", "size": fs + 1},
                         columnspacing=2.5, handletextpad=0.4)
    leg = axes[1].legend(handles=[Line2D([], [], marker="^", ls="", color=CONF_COLOR, ms=10),
                                  Line2D([], [], marker="^", ls="", color=CALC_COLOR, ms=10)],
                         labels=[f"confirmed location: {human(d['confirmed'])}",
                                 f"calculated from picks: {human(d['located'] - d['confirmed'])}"],
                         title=f"Stations: {human(d['stations'])} ({human(d['located'])} located)",
                         loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=fs,
                         title_fontproperties={"weight": "bold", "size": fs + 1}, columnspacing=2.5,
                         handletextpad=0.4)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"{version}: {path}", flush=True)


def maps():
    for version, root in VERSIONS.items():
        d = load(root)
        print(f"{version}: {d['networks']} networks, {len(d['events'])} events, {d['p']} P, {d['s']} S, "
              f"{d['stations']} stations ({d['located']} located, {d['confirmed']} confirmed)", flush=True)
        path = OUT / f"utdquake_overview_{version}.png"
        draw(version, d, path)
        if version == LATEST:
            (OUT / "utdquake_overview.png").write_bytes(path.read_bytes())


def gif(fps: float = 0.7, max_frames: int = 50):
    """The networks' overview figures (latest version) as one looping GIF, as test/scripts/fig/test_figs_overview.py."""
    import imageio.v2 as imageio
    from PIL import Image
    folder = VERSIONS[LATEST] / "figures" / "networks"
    first = ["av", "nc", "ci", "uu", "nm", "ok", "tx", "R03", "R11", "MEX", "hv", "CATAC", "pr", "RSNC", "FUNV",
             "VAO", "SJA", "PRE", "ISK", "INMG", "LDG", "AFAD", "NOA", "ATH", "BEO", "JMA", "DJA", "TAP", "R09",
             "R10", "R01"]
    images = {p.parent.name: p for p in folder.glob("*/*_overview.png")}
    order = [n for n in first if n in images] + sorted(n for n in images if n not in first)
    order = order[:max_frames]
    size = max((Image.open(images[n]).size for n in order), key=lambda s: s[0] * s[1])
    frames = [np.array(Image.open(images[n]).convert("RGB").resize(size, Image.Resampling.LANCZOS)) for n in order]
    path = OUT / "all_networks_overview.gif"
    imageio.mimsave(path, frames, duration=1000 / fps, loop=0)
    print(f"gif: {len(frames)} frames {size} -> {path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    {"maps": maps, "gif": gif}[sys.argv[1]]()
