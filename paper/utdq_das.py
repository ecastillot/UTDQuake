import os 
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
os.environ["UTDQUAKE_DAS_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

from pathlib import Path
import utdquake as utdq

from utdquake.core.config import get_utdq_paths, get_hf_entry
from utdquake.utils.plot import plot_overview


from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import shapely.geometry as sgeom

from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import matplotlib.font_manager as fm
import pyproj
import numpy as np


fig_path = Path(__file__).parent / "utdq_das.png"
dataset = utdq.Dataset(das=True)
print(dataset)
network = dataset.get_network("GCI")
print(network)

region = [-157, -150, 58.5, 64.5 ]

events = network.events
stations = network.stations

fig, axes = plot_overview(events=events, 
                      stations=stations,
                      analysis=network.description,
                      das=network.das,
                      region = region,
                      consider_calculated_stations=False,
                      is_alaska=False,
                      savepath=fig_path,
                      show=False)

pos_ax_inset = [0.18, 0.35, 0.3, 0.3] 
inset_region = [-153, -151, 59, 60.5] 
ax_inset = fig.add_axes(
                    pos_ax_inset,   # position in figure
                    projection=ccrs.PlateCarree()
                )
ax_inset.set_extent(inset_region, crs=ccrs.PlateCarree())
ax_inset.add_feature(cfeature.COASTLINE)
ax_inset.add_feature(cfeature.BORDERS, linestyle=':')
ax_inset.add_feature(cfeature.STATES, linestyle=':')
ax_inset.add_feature(cfeature.LAND)
ax_inset.add_feature(cfeature.OCEAN)
ax_inset.add_feature(cfeature.LAKES, alpha=0.5)

ax_inset.scatter(
        events['longitude'],
        events['latitude'],
        color="#ec7524",
        s=15,
        alpha=1,
        edgecolor="#ec7524",
        transform=ccrs.PlateCarree()
    )

confirmed_mask = stations[['confirmed_longitude', 'confirmed_latitude']].notna().all(axis=1)
for c,cable in stations.groupby("station"):

    #change channel to float and sort by it, then plot as a line
    cable["channel"] = cable["channel"].astype(float)
    cable = cable.sort_values("channel")

    das_stations = cable.loc[confirmed_mask]

    ax_inset.plot(
        das_stations["confirmed_longitude"],
        das_stations["confirmed_latitude"],
        color="green",
        linewidth=2,
        alpha=1,
        transform=ccrs.PlateCarree(),
    )

lon_min, lon_max, lat_min, lat_max = inset_region
rect = sgeom.box(lon_min, lat_min, lon_max, lat_max)

mark_inset(
            axes[1],
            ax_inset,
            loc1=1,
            loc2=3,
            fc="none",
            ec="black"
        )

ax_inset.set_xticks([])
ax_inset.set_yticks([])



# --- Scale bar ---
proj = pyproj.Geod(ellps="WGS84")

# Length of scale bar in km
length_km = 25

# Reference latitude for conversion
lat0 = np.mean(inset_region[2:])

# Convert km to degrees longitude approximately
km_per_deg_lon = 111.32 * np.cos(np.deg2rad(lat0))
length_deg = length_km / km_per_deg_lon

scalebar = AnchoredSizeBar(
    ax_inset.transData,
    length_deg,                 # length in data coordinates
    f"{length_km} km",          # label
    loc='lower left',
    pad=0.5,
    color='black',
    frameon=False,
    size_vertical=0.01,
    fontproperties=fm.FontProperties(size=8)
)

ax_inset.add_artist(scalebar)


fig.savefig(fig_path, dpi=300)


