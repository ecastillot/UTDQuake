import matplotlib.pyplot as plt
import numpy as np
from .phase_trend import GlobalTrendFilter, LocalTrendFilter
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from ..utils.utils import human_format
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import MultipleLocator
import numpy as np

def plot_phase_travel_time_qc(gd_df,bd_df, phase, log=None, 
                              local_model=None,
                              global_model=None,
                              fit_xy_limits= True,
                              text=True,
                              legend=True,
                                ax=None):

    x_col="travel_time"
    y_col="linear_hyp_distance"

    if ax is None:
        fig, ax = plt.subplots(figsize=(4, 4))

    if gd_df.empty and bd_df.empty:
        if ax:
            ax.set_title(phase)
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", 
                va="center", fontsize=12, color="black")
            ax.set_xticklabels([])
            ax.set_yticklabels([])
        return  ax


    y_model = np.linspace(gd_df[y_col].min(), gd_df[y_col].max(), 100)

    if global_model is not None:
        gf = GlobalTrendFilter(global_trends={phase: global_model})

        (x_global, 
        lower_global, 
        upper_global) = gf.compute_bounds(y_model, phase=phase)

        gf_info = gf.to_dict()
        k = gf_info[phase]["k"]

        x_min, x_max = x_global.min(), x_global.max()
        # Shade LEFT rejected region
        ax.fill_betweenx(
            y_model,
            upper_global,
            upper_global.max(),
            color="gray",
            alpha=0.2
        )

        ax.fill_betweenx(
            y_model,
            lower_global.min(),
            lower_global,
            color="gray",
            alpha=0.2
        )

        # ax.plot(x_global, y_model, color="black", label="Global Trend")

        ax.plot(lower_global, y_model, "--", color="black", lw=1, 
                # label=f"Global\n± {int(k)}σ"
                label=f"GT"
                )
        ax.plot(upper_global, y_model, "--", color="black", lw=1)

    if local_model is not None:
        k = local_model.config.k_dict.get(phase, None)
        (x_local,
        lower_local,
        upper_local) = local_model.compute_bounds(y_model, k=k)

        ax.plot(x_local, y_model, color="red", lw=1)
        ax.plot(lower_local, y_model, "--", color="red", lw=1, 
                label=f"LT: ±{int(k)}σ")
        ax.plot(upper_local, y_model, "--", color="red", lw=1)

    nan_counts = gd_df[[x_col, y_col]].isna().sum(axis=1).sum()
    gd_counts = len(gd_df)

    msg = ""
    if log is not None:

        msg += "--Remotion--\n"
        for step in log:

            if "global_trend" in step["name"].lower() and step["phase"] == phase:
                name = "GT"
            elif "local_trend" in step["name"].lower() and step["phase"] == phase:
                name = "LT"
            else:
                name = step["name"]

            removed_counts = step["removed"]
            msg += f"{name}: {human_format(removed_counts)}\n"


        msg += "----Total----\n"
        msg += f"nan: {human_format(nan_counts)}\n"
        msg += f"good: {human_format(gd_counts)}\n"
        msg += "------------\n"
        msg += f"{human_format(nan_counts + gd_counts)}"

        if text and ax is not None:
            ax.text(
                    0.98, 0.02,   # x near right, y near bottom
                    msg,
                    transform=ax.transAxes,
                    horizontalalignment="right",
                    verticalalignment="bottom",
                    fontsize=9,
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
                )


    # scatter all points
    ax.scatter(bd_df[x_col], bd_df[y_col], s=2, color="gray", alpha=1)
    ax.scatter(gd_df[x_col], gd_df[y_col], s=2, color="black", alpha=1)


    if fit_xy_limits:
        ax.set_xlim(0, gd_df[x_col].max())
        # ax.set_ylim(0, fit_info["y_fit"].max())

        ymin = 0  # or maybe a bit lower than min(y)
        ymax_data = gd_df[y_col].max()  # or max(y) if you want to consider the data range

        # Add margin on top and bottom (so equation won’t overlap)
        y_margin_top = 0.05 * ymax_data   # 5% space on top
        y_margin_bottom = 0.07 * ymax_data  # 5% space on bottom

        ax.set_ylim(ymin - y_margin_bottom, ymax_data)

        # ax.set_ylim(0,50)  # Ensure y-axis starts at 0
        # ax.set_xlim(0,50)  # Ensure y-axis starts at 0

    #x and y axis in scientific notation
    ax.ticklabel_format(style='sci', axis='both', scilimits=(0,0))


    ax.set_title(phase)

    # Access offset text objects
    ax.xaxis.get_offset_text().set_fontsize(12)
    ax.xaxis.get_offset_text().set_fontweight('bold')
    ax.xaxis.get_offset_text().set_fontfamily('serif')   # or 'sans-serif', 'monospace'

    ax.yaxis.get_offset_text().set_fontsize(12)
    ax.yaxis.get_offset_text().set_fontweight('bold')
    ax.yaxis.get_offset_text().set_fontfamily('serif')

    if x_col == "travel_time":
        ax.set_xlabel("Travel Time (s)",fontsize=14,
                    labelpad=10)
    elif x_col == "linear_hyp_distance":
        ax.set_xlabel("Hyp. Distance (km)",fontsize=14,
                        labelpad=10)

    if y_col == "linear_hyp_distance":
        ax.set_ylabel("Hyp. Distance (km)",fontsize=14)
    elif y_col == "travel_time":
        ax.set_ylabel("Travel Time (s)",fontsize=14)

    if legend:
        if text:
            ax.legend(
                title="QC",
                fontsize=8,
                loc="lower right",
                alignment="right",
                bbox_to_anchor=(0.99, 0.25)   # above text
            )
        else:
            ax.legend(fontsize=8,
                title="QC",
                      alignment="right",
                        loc="lower right")

    return ax

def tune_zoomed_travel_time_qc(axins, xlim=(0,15), ylim=(0,50)):

    ymax = ylim[1]
    xmax = xlim[1]

    def hide_edges_x(x, pos):
        if np.isclose(x, 0) or np.isclose(x, xmax):
            return ""
        return f"{x:g}"

    def hide_edges_y(y, pos):
        if np.isclose(y, 0) or np.isclose(y, ymax):
            return ""
        return f"{y:g}"

    x_multiplier = int(np.floor(xlim[1] / 3)  )
    y_multiplier = int(np.floor(ylim[1] / 3))


    axins.set_ylim(*ylim)  # Ensure y-axis starts at 0
    axins.set_xlim(*xlim)  # Ensure y-axis starts at 0
    axins.tick_params(labelsize=8)
    # Move y-axis to the right
    axins.yaxis.tick_right()
    axins.yaxis.set_label_position("left")
    axins.xaxis.set_major_locator(MultipleLocator(x_multiplier))
    axins.xaxis.set_major_formatter(FuncFormatter(hide_edges_x))
    axins.yaxis.set_major_formatter(FuncFormatter(hide_edges_y))

    axins.tick_params(axis='y', direction='in',pad=-12)
    # axins.ticklabel_format(style="plain", axis='both', scilimits=(0,0))
    axins.yaxis.get_offset_text().set_fontsize(8)
    axins.yaxis.get_offset_text().set_fontweight('bold')
    axins.yaxis.get_offset_text().set_fontfamily('serif')
    #no labels in the inset
    axins.set_xlabel("")
    axins.set_ylabel("")
    axins.set_title("")
    return axins

def plot_travel_time_qc(gd_df,bd_df,
                        network,
                        figsize=(8, 12),
                        log=None, 
                        show_zoomed_inset=True,
                        local_models=None,
                        global_models=None,
                        fit_xy_limits=False,
                        xy_inset_limits=None,
                        save_path=None,
                        ):

    fig, axes = plt.subplots(2, 3, figsize=figsize)
    fig.subplots_adjust(wspace=0.5)
    axes = axes.reshape(2, 3)

    phase_order = ["P", "Pn", "Pg", "S", "Sn", "Sg"]

    for i in range(2):
        for j in range(3):
            ax = axes[i, j]
            phase = phase_order[i*3 + j]

            gd_df_phase = gd_df[gd_df["phase"] == phase]
            bd_df_phase = bd_df[bd_df["phase"] == phase]

            phase_local_model = local_models.get(phase) if local_models else None
            phase_global_model = global_models.get(phase) if global_models else None
            phase_log = log.get_steps_by_phase(phase) if log else None

            print(phase_log)

            ax = plot_phase_travel_time_qc(gd_df_phase,
                                        bd_df_phase,
                                        phase=phase,
                                        log=phase_log, 
                                        local_model=phase_local_model,
                                        global_model=phase_global_model,
                                            fit_xy_limits=fit_xy_limits,
                                        ax=ax)
            
            if show_zoomed_inset:
                xlim, ylim = (0,15), (0,50)

                if xy_inset_limits is not None:
                    phase_lim = xy_inset_limits.get(phase, None)
                    xlim = phase_lim.get("x", xlim)
                    ylim = phase_lim.get("y", ylim)


                axins = inset_axes(ax, width="35%", height="35%", loc="upper left")
                axins = plot_phase_travel_time_qc(gd_df_phase,
                                            bd_df_phase,
                                            phase=phase,
                                            log=phase_log, 
                                            local_model=phase_local_model,
                                            global_model=phase_global_model,
                                                fit_xy_limits=False,
                                            text=False,
                                            legend=False,
                                            ax=axins)
                axins = tune_zoomed_travel_time_qc(axins, 
                                                    xlim=xlim, 
                                                    ylim=ylim)

            

            # ✅ Only left column gets Y label
            if j != 0:
                ax.set_ylabel("")

            # ✅ Only bottom row gets X label
            if i != 1:
                ax.set_xlabel("")
    
    fig.suptitle(f"{network}", fontsize=16, fontweight='bold')
    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=300)

    return fig, axes