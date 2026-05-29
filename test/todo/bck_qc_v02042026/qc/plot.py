import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from ..utils.utils import human_format
from .config import GLOBAL_TRENDS_DEFAULTS_DEG2
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import MultipleLocator
import numpy as np
from matplotlib.ticker import AutoMinorLocator
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset


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
    
    # # Move y-axis to the right
    # axins.yaxis.tick_right()
    # axins.yaxis.set_label_position("right")
    axins.xaxis.set_major_locator(MultipleLocator(x_multiplier))
    axins.xaxis.set_major_formatter(FuncFormatter(hide_edges_x))
    axins.yaxis.set_major_formatter(FuncFormatter(hide_edges_y))

    axins.tick_params(axis='y', direction='in',pad=-12)
    # axins.ticklabel_format(style="plain", axis='both', scilimits=(0,0))
    axins.yaxis.get_offset_text().set_fontsize(8)
    axins.yaxis.get_offset_text().set_fontweight('bold')
    axins.yaxis.get_offset_text().set_fontfamily('serif')

    axins.grid(True, which="both", axis="y",
            linestyle="--", linewidth=0.5, alpha=0.3)
    
    #no labels in the inset
    axins.set_xlabel("")
    axins.set_ylabel("")
    axins.set_title("")
    return axins

def plot_single_tt_qc(df, phase,
                    model=None,  
                    classifier = None,
                    show_stats = None,
                    show_global=True,
                    show_text=True,
                    distance_col="linear_hyp_distance", 
                    tt_col="travel_time",
                    x_limits=None, y_limits=None,
                    ax=None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(6,4))
    
    if show_stats is None:
        show_stats = ["tt_p50"]
        # show_stats = ["tt_p1","tt_p25","tt_p50",
                    #  "tt_p75","tt_p99","sigma"]

    if classifier is None:
        classifier = {"method":"sigma","p_low":0.25,"p_high":0.75,
                      "k":2}
        
    df = df[df["phase"]==phase]
    df = df.dropna(subset=[distance_col, tt_col])
    df = df.sort_values(by=distance_col,ignore_index=True)
    x = df[distance_col]
    y = df[tt_col]

    #insert 0 and 0 in x and y

    # ax.scatter(x, y, s=2, alpha=0.6,
    #             color="black")

    if show_global and phase in GLOBAL_TRENDS_DEFAULTS_DEG2:

        info = GLOBAL_TRENDS_DEFAULTS_DEG2[phase]

        poly = np.poly1d(info["coefficients"])
        sigma = info.get("sigma_median")
        k = info.get("k", 5)

        xg = np.asarray(x)

        y_pred = poly(xg)
        lower_g = np.maximum(0, y_pred - k * sigma)
        upper_g = y_pred + k * sigma

        ax.plot(xg, upper_g,
                color="blue",
                linestyle=":",
                linewidth=1,
                label="Global bounds")

        ax.plot(xg, lower_g,
                color="blue",
                linestyle=":",
                linewidth=1)

    if model is not None:
        l_bins = model.model_df["dist_min"]. values
        r_bins = model.model_df["dist_max"]. values
        c_bins = model.model_df["distance_center"]. values
        bins = np.unique(np.concatenate([l_bins, r_bins]))
        median = model.model_df["tt_p50"]. values

        if classifier.get("method") == "sigma":
            sigma = model.model_df["sigma"]. values
            sigma_factor = classifier.get("k", 2)
            upper_model = median + sigma_factor * sigma
            lower_model = median - sigma_factor * sigma
        elif classifier.get("method") == "percentile":
            p_low = classifier.get("p_low", 0.25)
            p_high = classifier.get("p_high", 0.75)
            lower_model = model.model_df[f"tt_p{int(p_low*100)}"]. values
            upper_model = model.model_df[f"tt_p{int(p_high*100)}"]. values
        else:
            raise ValueError(f"Unknown classification method: {classifier.get('method')}")
            
        lower = np.interp(x, c_bins, lower_model)
        upper = np.interp(x, c_bins, upper_model)

        inside = (y >= lower) & (y <= upper)
        outside = ~inside

        label = f'{classifier.get("k")}σ' if classifier.get("method") == "sigma" \
            else f'[P{classifier.get("p_low")}-P{classifier.get("p_high")}]'

        ax.scatter(x[outside], y[outside], s=2, alpha=0.6,
                color="red",label="Outside bounds")
        ax.scatter(x[inside], y[inside], s=2, alpha=0.6,
                color="black", label="Inside bounds")
        
        ax.plot(x, upper, label=label,color="green",
                linestyle="--", linewidth=0.7, alpha=1)
        ax.plot(x, lower, color="green",
                linestyle="--", linewidth=0.7, alpha=1)
        
        if show_text:
            n_total = len(x)
            n_inside = len(x)-len(x[outside]) 
            text = f"{human_format(n_inside)}/{human_format(n_total)}"
            ax.text(0.95, 0.1, text,
                            transform=ax.transAxes,
                        bbox=dict(facecolor="white",
                            edgecolor="black",
                            boxstyle="round,pad=0.3",
                            alpha=1),    
                        fontsize=12,
                        ha="right", va="bottom")


        for col in show_stats:
            model_df = model.model_df
            model_df = model_df.sort_values(by="distance_center", ignore_index=True)
            model_df = model_df.dropna(subset=[col, "distance_center"])
            model_df = model_df.drop_duplicates(subset=["distance_center"])

            tt = model_df[col].values
            dd = model_df["distance_center"].values

            if len(dd) < 3:  # cannot fit degree 2 polynomial
                print(f"Skipping {col}: not enough points to fit polynomial")
                continue

            label = col.split("_")[1] if "_" in col else col
            label = label.upper() 
            if col == "tt_p50":
                ax.plot(dd, tt, label=label,
                        linestyle="-", 
                        color="green",
                        linewidth=1, alpha=1)
            else:
                ax.plot(dd, tt, label=label,
                # ax.plot(x, tt_fit, label=col,
                        linestyle="..", 
                        linewidth=0.5, alpha=1)

            

        for c in bins:
            ax.axvline(c, color="black", linestyle="--", 
                       linewidth=0.5, alpha=0.2)

    
    ax.grid(True, which="both", axis="y",
            linestyle="--", linewidth=0.5, 
            alpha=0.3)

    if x_limits is not None:
        ax.set_xlim(*x_limits)
    if y_limits is not None:
        ax.set_ylim(*y_limits)

    return ax
    


def plot_tt_qc(df,models=None,add_inset=True,
            show_stats=None,
            show_global=True,
            distance_col="linear_hyp_distance", 
            tt_col="travel_time",
            x_inset_limits=(0,30),
            y_inset_limits=(0,10),
            savepath=None
            ):

    phase_order=("P", "Pn", "Pg", "S", "Sn", "Sg")

    fig, axes = plt.subplots(2, 3, figsize=(12,8))
    axes = axes.flatten()

    all_axins = []
    legend_handles = []
    legend_labels = []
    for idx, phase in enumerate(phase_order):

        ax = axes[idx]
        phase_df = df[df["phase"] == phase]

        nan_mask = phase_df[distance_col].isna() | phase_df[tt_col].isna()
        nan_phase_df = phase_df[nan_mask]
        phase_df = phase_df[~nan_mask]

        model = models.get(phase) if models is not None else None

        if phase_df.empty:
            ax.set_title(f"{phase} (no data)",fontweight="bold")
            ax.axis("off")
            continue
        
        ax.set_title(phase,fontweight="bold")
        ax = plot_single_tt_qc(phase_df,phase=phase,
                               model=model, 
                               show_stats=show_stats,
                               show_global=show_global,
                               ax=ax,
                        distance_col=distance_col, tt_col=tt_col,
                        x_limits=(0,phase_df[distance_col].max()), 
                        y_limits=(0,phase_df[tt_col].max())
                        )

        # Only show y-label for left column axes (0,3)
        if idx in [0, 3]:
            ax.set_ylabel("Travel time (s)", fontsize=14)
        else:
            ax.set_ylabel("")

        # Only show x-label for bottom row axes (3,4,5)
        if idx in [3, 4, 5]:
            ax.set_xlabel("Distance (km)", fontsize=14)
        else:
            ax.set_xlabel("")

        # collect handles for the legend only once
        if not legend_handles:
            for h, l in zip(ax.get_legend_handles_labels()[0], ax.get_legend_handles_labels()[1]):
                legend_handles.append(h)
                legend_labels.append(l)

        if add_inset:
            axins = inset_axes(ax, width="35%", height="35%", loc="upper left")
            axins = plot_single_tt_qc(phase_df, phase=phase, 
                                      model=model,
                                      show_stats=show_stats,
                                      show_global=show_global,
                                      show_text=False,
                                      ax=axins,
                                    distance_col=distance_col, tt_col=tt_col,
                                    x_limits=x_inset_limits, y_limits=y_inset_limits)
            #print ax limits
            print(f"Phase: {phase}, Inset xlim: {ax.get_xlim()}, Inset ylim: {ax.get_ylim()}")
            tune_zoomed_travel_time_qc(axins, xlim=x_inset_limits, 
                                    ylim=y_inset_limits)
            mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.5")
            all_axins.append(axins)


    fig.tight_layout()

    # Add a single legend at the bottom
    fig.legend(
            legend_handles, legend_labels,
            loc='lower center',       # still horizontally centered
            bbox_to_anchor=(0.5, -0.05),  # move it further down outside the plot
            ncol=len(legend_labels),
            markerscale=4,
            frameon=True,
            prop={'size': 12}             # legend text size
        )

    if savepath:
        fig.savefig(savepath, dpi=300, bbox_inches='tight')
        print(f"Saved to {savepath}")

    return fig, axes, all_axins

if __name__ == "__main__":
    import pandas as pd
    from travel_time import MultiTravelTimeModel
    network = "TAP"
    path = f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/results/picks/network={network}.csv"
    df = pd.read_csv(path)
    model_path = f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/results/qc/network={network}.csv"
    
    load = MultiTravelTimeModel.load(model_path)
    models = load.models
    # model=pd.read_csv(model_path)
    fig_path = f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/results/picks/network={network}.png" 
    plot_tt_qc(df, models=models, add_inset=True, savepath=fig_path)
