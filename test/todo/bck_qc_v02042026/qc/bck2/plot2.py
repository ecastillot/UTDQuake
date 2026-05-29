import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.ticker import FuncFormatter, MultipleLocator
from ..utils.utils import human_format

def plot_phase_travel_time_qc(
    gd_df, bd_df, phase,
    local_model=None, global_model=None,
    log=None, fit_xy_limits=True, text=True, legend=True, ax=None
):
    x_col, y_col = "travel_time", "linear_hyp_distance"

    if ax is None:
        fig, ax = plt.subplots(figsize=(4,4))

    if gd_df.empty and bd_df.empty:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", va="center")
        return ax

    y_vals = np.linspace(gd_df[y_col].min(), gd_df[y_col].max(), 100)

    # ---------- Global Trend ----------
    if global_model:
        x_global, lower_global, upper_global = global_model.compute_bounds(y_vals, phase)
        ax.fill_betweenx(y_vals, lower_global, upper_global, color="gray", alpha=0.2, label="GT ±σ")
        ax.plot(lower_global, y_vals, "--", color="black", lw=1)
        ax.plot(upper_global, y_vals, "--", color="black", lw=1)

        # Color points inside/outside bounds
        inside_mask = (gd_df[x_col] >= lower_global) & (gd_df[x_col] <= upper_global)
        ax.scatter(gd_df.loc[inside_mask, x_col], gd_df.loc[inside_mask, y_col],
                   s=3, color="green", label="Inside GT")
        ax.scatter(gd_df.loc[~inside_mask, x_col], gd_df.loc[~inside_mask, y_col],
                   s=3, color="red", label="Outside GT")
    else:
        ax.scatter(gd_df[x_col], gd_df[y_col], s=3, color="black", label="Good")
    
    # ---------- Local Trend ----------
    if local_model:
        k = local_model.config.k_dict.get(phase, None)
        x_local, lower_local, upper_local = local_model.compute_bounds(y_vals, k=k)
        ax.fill_betweenx(y_vals, lower_local, upper_local, color="red", alpha=0.15, label=f"LT ±{int(k)}σ")
        ax.plot(x_local, y_vals, color="red", lw=1)
        ax.plot(lower_local, y_vals, "--", color="red", lw=1)
        ax.plot(upper_local, y_vals, "--", color="red", lw=1)

    # ---------- Bad points ----------
    ax.scatter(bd_df[x_col], bd_df[y_col], s=2, color="gray", alpha=1, label="Removed")

    # ---------- QC log text ----------
    if log and text:
        msg = ""
        for step in log:
            removed_counts = step["removed"]
            msg += f"{step['name']}: {human_format(removed_counts)}\n"
        msg += f"Good: {len(gd_df)}\nRemoved: {len(bd_df)}"
        ax.text(0.98, 0.02, msg, transform=ax.transAxes,
                horizontalalignment="right", verticalalignment="bottom",
                fontsize=8, bbox=dict(facecolor="white", alpha=0.8))

    # ---------- Axis formatting ----------
    if fit_xy_limits:
        ax.set_xlim(0, gd_df[x_col].max()*1.05)
        ax.set_ylim(0, gd_df[y_col].max()*1.05)

    ax.set_xlabel("Travel Time (s)")
    ax.set_ylabel("Hyp. Distance (km)")
    ax.set_title(phase)
    ax.ticklabel_format(style='sci', axis='both', scilimits=(0,0))

    if legend:
        ax.legend(fontsize=7, loc="lower right")

    return ax

# ---------- Zoomed inset ----------
def add_zoomed_inset(ax, gd_df, bd_df, phase, local_model=None, global_model=None,
                     xlim=None, ylim=None):
    if gd_df.empty:
        return None

    # Automatic zoom: 5th-95th percentile of travel times and distances
    x_col, y_col = "travel_time", "linear_hyp_distance"
    if xlim is None:
        xlim = np.percentile(gd_df[x_col], [5, 95])
    if ylim is None:
        ylim = np.percentile(gd_df[y_col], [5, 95])

    axins = inset_axes(ax, width="35%", height="35%", loc="upper left")
    axins = plot_phase_travel_time_qc(gd_df, bd_df, phase,
                                      local_model=local_model, global_model=global_model,
                                      fit_xy_limits=False, text=False, legend=False,
                                      ax=axins)
    axins.set_xlim(*xlim)
    axins.set_ylim(*ylim)
    axins.set_xticks([])
    axins.set_yticks([])
    return axins

# ---------- Full multi-phase plot ----------
def plot_travel_time_qc(gd_df, bd_df, network,
                        phases=["P","Pn","Pg","S","Sn","Sg"],
                        local_models=None, global_models=None,
                        log=None, figsize=(10,6), show_zoomed_inset=True,
                        save_path=None):
    n_phases = len(phases)
    ncols = 3
    nrows = int(np.ceil(n_phases / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes = axes.flatten()

    for i, phase in enumerate(phases):
        ax = axes[i]
        gd_df_phase = gd_df[gd_df["phase"] == phase]
        bd_df_phase = bd_df[bd_df["phase"] == phase]

        local_model = local_models.get(phase) if local_models else None
        global_model = global_models.get(phase) if global_models else None
        phase_log = log.get_steps_by_phase(phase) if log else None

        ax = plot_phase_travel_time_qc(gd_df_phase, bd_df_phase, phase,
                                       local_model=local_model, global_model=global_model,
                                       log=phase_log, ax=ax)

        if show_zoomed_inset:
            add_zoomed_inset(ax, gd_df_phase, bd_df_phase, phase,
                             local_model=local_model, global_model=global_model)

        # Clean labels for non-left and non-bottom axes
        if i % ncols != 0:
            ax.set_ylabel("")
        if i < ncols*(nrows-1):
            ax.set_xlabel("")

    # Hide unused axes
    for j in range(n_phases, len(axes)):
        axes[j].axis("off")

    fig.suptitle(network, fontsize=16, fontweight='bold')
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300)
    return fig, axes