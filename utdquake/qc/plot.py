import matplotlib.pyplot as plt
import numpy as np
from .phase_trend import GlobalTrendFilter, LocalTrendFilter

def plot_phase_travel_time_qc(gd_df,bd_df, phase, log=None, 
                              local_model=None,
                              global_model=None,
                            ax=None):

    x_col="travel_time"
    y_col="linear_hyp_distance"

    if ax is None:
        fig, ax = plt.subplots(figsize=(4, 4))


    y_model = np.linspace(gd_df[y_col].min(), gd_df[y_col].max(), 100)

    if global_model is not None:
        gf = GlobalTrendFilter()

        (x_global, 
        lower_global, 
        upper_global) = gf.compute_bounds(y_model, phase=phase)
        ax.plot(x_global, y_model, color="green", label="Global Trend")

        ax.plot(lower_global, y_model, "--", color="green", lw=1, label="GT Bounds")
        ax.plot(upper_global, y_model, "--", color="green", lw=1)

    # if gd_df.empty or bd_df.empty:
    #     if ax:
    #         ax.set_title(phase)
    #         ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", 
    #             va="center", fontsize=12, color="black")
    #         ax.set_xticklabels([])
    #         ax.set_yticklabels([])
    #     return  ax

    # x = df_phase[x_col].values
    # y = df_phase[y_col].values

    # scatter all points
    ax.scatter(gd_df[x_col], gd_df[y_col], s=2, color="black", alpha=1)
    ax.scatter(bd_df[x_col], bd_df[y_col], s=2, color="gray", alpha=1)

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

    return ax

    

def plot_travel_time_qc(gd_df,bd_df,figsize=(8, 12),
                        log=None, 
                        local_models=None,
                        global_models=None,
                        save_path=None
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

            local_model = local_models.get(phase) if local_models else None
            global_model = global_models.get(phase) if global_models else None

            ax = plot_phase_travel_time_qc(gd_df_phase,
                                        bd_df_phase,
                                        phase=phase,
                                        log=log, 
                                        local_model=local_model,
                                        global_model=global_model,
                                        ax=ax)


            # ✅ Only left column gets Y label
            if j != 0:
                ax.set_ylabel("")

            # ✅ Only bottom row gets X label
            if i != 1:
                ax.set_xlabel("")
    
    
    
    fig.tight_layout()

    if save_path is not None:
        fig.savefig(save_path, dpi=300)

    return fig, axes