import sys
lib = "/groups/igonin/ecastillo/UTDQuake"
if lib not in sys.path:
    sys.path.append(lib)

import os
import glob
import numpy as np
import pandas as pd
import obsplus
from matplotlib.patches import Rectangle
from utdquake.utils.plot import plot_network_map,human_format
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# === CONFIG ===

output_dir = "/groups/igonin/ecastillo/UTDQuake/test/10132025/plots"
global_region = None  # Set to None for global, or specify as (-180, 180, -90, 90)


# === Final global overview ===


df_all_events = pd.read_csv(os.path.join(output_dir, "all_events.csv"))
df_all_stations = pd.read_csv(os.path.join(output_dir, "all_stations.csv"))

n_p_picks = df_all_events['p_phase_count'].sum()
n_s_picks = df_all_events['s_phase_count'].sum()

df_all_stations.drop_duplicates(subset=["network","station"], inplace=True)
n_total_stations = len(df_all_stations)
confirmed_stations = df_all_stations[df_all_stations["confirmed"]==True]
calculated_stations = df_all_stations[df_all_stations["calculated"]==True]

n_confirmed_stations = len(confirmed_stations)
n_calculated_stations = len(calculated_stations)

print(df_all_events.describe())
exit()

analysis = {
            "Events": len(df_all_events),
            "Total Stations": n_total_stations,
            "Calculated Stations": n_calculated_stations,
            "Confirmed Stations": n_confirmed_stations,
            "P arrivals": n_p_picks,
            "S arrivals": n_s_picks,
    }

def setup_map(ax, region):
    ax.set_extent(region, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.STATES, linestyle=':')
    ax.add_feature(cfeature.LAND, edgecolor='black')
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)

    # Gridlines (labels on bottom/right)
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray',
                      alpha=0.7, linestyle='--')
    gl.top_labels = True
    gl.left_labels = True  # right side labels instead
    gl.right_labels = False
    gl.bottom_labels = True

    return ax,gl

region = (-180, 180, -90, 90) if global_region is None else global_region

# Create figure with shared X-axis
fig, (ax1, ax2) = plt.subplots(
    nrows=2, ncols=1,
    figsize=(12, 8), dpi=300,
    subplot_kw={'projection': ccrs.PlateCarree()},
    sharex=True
)

# ---- Earthquakes (top subplot) ----
ax1,gl1 = setup_map(ax1, region)
gl1.top_labels = True
gl1.right_labels = False
gl1.left_labels = True  # right side labels instead
gl1.bottom_labels = False
ax1.scatter(
    df_all_events['longitude'],
    df_all_events['latitude'],
    # alpha=0.5, 
    # color="red",
    color="#ec7524",
    transform=ccrs.PlateCarree(),
    label='Earthquakes'
)
ax1.legend(loc='lower right', fontsize=12)

ax1.text(
    0.02, 0.05,  # bottom-left
    f"Events: {human_format(analysis.get('Events', len(df_all_events)))}\n"
    f"P Arrivals: {human_format(analysis.get('P arrivals', 0))}\n"
    f"S Arrivals: {human_format(analysis.get('S arrivals', 0))}",
    transform=ax1.transAxes,
    ha='left',
    va='bottom',
    fontsize=12,
    bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
)

# ---- Stations (bottom subplot) ----
ax2,gl2 = setup_map(ax2, region)
gl2.top_labels = False
gl2.right_labels = False
gl2.left_labels = True  # right side labels instead
gl2.bottom_labels = True
ax2.scatter(
    calculated_stations['calculated_longitude'],
    calculated_stations['calculated_latitude'],
    marker='^', c='green', s=40,
    alpha=0.7, transform=ccrs.PlateCarree(),
    label='Stations'
)
ax2.legend(loc='lower right', fontsize=12)

ax2.text(
    0.02, 0.05,  # bottom-left
    f"Total Stations: {human_format(analysis['Total Stations'])}\n"
    f"   Calculated: {human_format(analysis['Calculated Stations'])}\n"
    f"   Confirmed: {human_format(analysis['Confirmed Stations'])}",
    transform=ax2.transAxes,
    ha='left',
    va='bottom',
    fontsize=12,
    bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=1)
)

# plt.tight_layout()
plt.subplots_adjust(hspace=0.05)
overview_outfile = os.path.join(output_dir, "earthquakes_stations_overview.png")
plt.savefig(overview_outfile, dpi=300)
plt.close(fig)

print(f"✅ Saved: {overview_outfile}")
