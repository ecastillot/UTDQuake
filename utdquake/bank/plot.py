import string
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import matplotlib as mpl


def plot_earthquake_overview(
    earthquake_df,
    save_path=None,
    station_df=None,
    lon_range=None,
    lat_range=None,
    plot_start_time=None,
    plot_end_time=None,
    timeline_start=None,
    timeline_end=None,
    result_label="TexNet"
):
    """
    Generate a 3-panel overview plot of earthquake data.

    Parameters:
        earthquake_df (pd.DataFrame): DataFrame with earthquakes. Must include:
                                      'longitude', 'latitude', 'depth', 'magnitude', 'origin_time'.
        save_path (str, optional): Path to save the output figure. If None, the plot is not saved.
        station_df (pd.DataFrame, optional): DataFrame with station data. Must include
                                             'longitude' and 'latitude' columns.
        lon_range (tuple, optional): Longitude limits (min, max). Defaults to data range.
        lat_range (tuple, optional): Latitude limits (min, max). Defaults to data range.
        plot_start_time (datetime, optional): Zoomed-in plot start time. Defaults to timeline_start.
        plot_end_time (datetime, optional): Zoomed-in plot end time. Defaults to timeline_end.
        timeline_start (datetime, optional): Start of full timeline. Defaults to earliest event.
        timeline_end (datetime, optional): End of full timeline. Defaults to latest event.
        result_label (str): Label used for dataset in the map legend.

    Returns:
        fig (matplotlib.figure.Figure): The generated figure.
        axes (list): List of axes [ax_map, ax_depth, ax_time].
    """
    # Validate required columns in earthquake data
    required_cols = {'longitude', 'latitude', 'depth', 'magnitude', 'origin_time'}
    if not required_cols.issubset(earthquake_df.columns):
        raise ValueError(f"earthquake_df must contain columns: {required_cols}")

    # Validate station data if provided
    if station_df is not None:
        if not {'longitude', 'latitude'}.issubset(station_df.columns):
            raise ValueError("station_df must contain 'longitude' and 'latitude' columns")

    # Ensure origin_time is datetime
    earthquake_df["origin_time"] = pd.to_datetime(earthquake_df["origin_time"])

    # Set default map bounds if not provided
    if lon_range is None:
        lon_range = (earthquake_df["longitude"].min(), earthquake_df["longitude"].max())
    if lat_range is None:
        lat_range = (earthquake_df["latitude"].min(), earthquake_df["latitude"].max())

    # Set default time bounds if not provided
    if timeline_start is None:
        timeline_start = earthquake_df["origin_time"].min().to_pydatetime()
    if timeline_end is None:
        timeline_end = earthquake_df["origin_time"].max().to_pydatetime()
    if plot_start_time is None:
        plot_start_time = timeline_start
    if plot_end_time is None:
        plot_end_time = timeline_end

    # Create figure with GridSpec layout
    fig = plt.figure(figsize=(14, 8))
    grd = fig.add_gridspec(
        ncols=2, nrows=6, width_ratios=[1.5, 1], height_ratios=[1] * 6
    )

    # Panel (a): Map view
    ax0 = fig.add_subplot(grd[:3, 0])
    ax0.plot(earthquake_df["longitude"], earthquake_df["latitude"], 'k.', markersize=6, alpha=0.6)
    ax0.set_xlim(np.array(lon_range) + np.array([-0.05, 0.05]))
    ax0.set_ylim(np.array(lat_range) + np.array([-0.05, 0.05]))
    ax0.set_xlabel("Longitude (°)")
    ax0.set_ylabel("Latitude (°)")

    # Plot stations if provided
    if station_df is not None:
        ax0.plot(
            station_df["longitude"], station_df["latitude"],
            'r^', markersize=8, alpha=0.7, label="Stations"
        )

    # Dummy point for dataset label
    ax0.plot(lon_range[0] - 1, lat_range[0] - 1, 'k.', markersize=5, label=result_label)
    ax0.legend(loc="lower left")

    # Panel (b): Longitude vs. Depth
    ax1 = fig.add_subplot(grd[3:6, 0], sharex=ax0)
    ax1.plot(earthquake_df["longitude"], earthquake_df["depth"], 'k.', markersize=2, alpha=1.0)
    ax1.set_xlim(lon_range)
    ax1.set_ylim([0, 12])
    ax1.invert_yaxis()  # Depth increases downward
    ax1.grid(True, which='minor', linestyle='--', linewidth=0.5, alpha=0.5)
    ax1.grid(True, which='major', linestyle='--', linewidth=1.5)
    ax1.set_xlabel("Longitude (°)")
    ax1.set_ylabel("Depth (km)")

    # Convert magnitude to size for scatter
    earthquake_df["m"] = 2 * (1.1 ** earthquake_df["magnitude"])

    # Panel (c): Time vs. Count and Magnitude
    ax2 = fig.add_subplot(grd[1:5, 1])
    ax2.hist(
        earthquake_df["origin_time"],
        range=(timeline_start, timeline_end),
        # bins=mdates.drange(timeline_start, timeline_end, pd.Timedelta(weeks=4)),
        color="k", edgecolor="w", alpha=0.85, linewidth=0.5,
        label=f"Events = {len(earthquake_df)}"
    )
    ax2.set_ylabel("Count", color="black")
    ax2.set_xlabel("Date", color="black")
    ax2.autoscale(enable=True, axis='x', tight=True)
    # ax2.xaxis.set_major_locator(mdates.YearLocator())
    # ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    # ax2.xaxis.set_minor_locator(mdates.MonthLocator())
    ax2.grid(True, which='minor', linestyle='--', linewidth=0.5, alpha=0.5)
    ax2.grid(True, which='major', linestyle='--', linewidth=1.5)
    ax2.set_xlim(plot_start_time, plot_end_time)
    ax2.tick_params(axis='x', colors='black')
    ax2.tick_params(axis='y', colors='black')
    ax2.spines["bottom"].set_edgecolor('darkorange')
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax2.legend(loc='upper left', fontsize=12)

    # Overlay magnitude on secondary y-axis
    ax2_r = ax2.twinx()
    ax2_r.scatter(
        earthquake_df["origin_time"], earthquake_df["magnitude"],
        s=earthquake_df["m"], c='darkorange', edgecolor=None, alpha=0.3
    )
    ax2_r.set_ylabel('Magnitude', size=14, color="darkorange")
    ax2_r.spines["right"].set_edgecolor('darkorange')
    ax2_r.spines["right"].set_linewidth(2)
    ax2_r.tick_params(axis='y', colors='darkorange', labelsize=15, width=2.5, length=10)
    ax2.tick_params(labelbottom=True)

    # Add panel labels (a, b, c)
    axes = [ax0, ax1, ax2]
    for n, ax in enumerate(axes):
        ax.annotate(
            f"({string.ascii_lowercase[n]})",
            xy=(-0.1, 1.05), xycoords='axes fraction',
            ha='left', va='bottom', fontsize="large"
        )

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.1)

    # Save the figure if a path is specified
    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=300)

    return fig, axes

if __name__ == "__main__":
    path = "/groups/igonin/ecastillo/UTDQuake/test/bank/test_event_summary.csv"
    save_path = "/groups/igonin/ecastillo/UTDQuake/test/bank/test_event_summary.png"
    df = pd.read_csv(path)
    df["origin_time"] = pd.to_datetime(df["time"])
    df["depth"] = df["depth"]/1e3
    plot_earthquake_overview(df, save_path=save_path,)