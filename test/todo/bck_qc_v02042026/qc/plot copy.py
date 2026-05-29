import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from ..utils.utils import human_format
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import MultipleLocator
import numpy as np
from matplotlib.ticker import AutoMinorLocator
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
from matplotlib.lines import Line2D


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

    # axins.tick_params(axis='y', direction='in',pad=-12)
    # # axins.ticklabel_format(style="plain", axis='both', scilimits=(0,0))
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

def customize_legend(ax, scatter_labels=("Inside bounds", "Outside bounds"),
                     scatter_colors=("black", "red"), scatter_sizes=(8, 8),
                     loc="upper left", **kwargs):
    """
    Customize the legend so that only scatter points have larger markers,
    while keeping line plots unchanged.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes containing the plot.
    scatter_labels : tuple
        Labels of the scatter points to enlarge in the legend.
    scatter_colors : tuple
        Colors of the scatter points.
    scatter_sizes : tuple
        Marker sizes for the scatter points in the legend.
    loc : str
        Legend location.
    kwargs : dict
        Additional keyword arguments passed to ax.legend().
    """
    # Create proxy artists for the scatter points
    proxy_scatters = [
        Line2D([0], [0], marker='o', color='w', label=label,
               markerfacecolor=color, markersize=size, alpha=0.6)
        for label, color, size in zip(scatter_labels, scatter_colors, scatter_sizes)
    ]

    # Get existing line handles and labels
    handles, labels = ax.get_legend_handles_labels()
    line_handles = [h for h, l in zip(handles, labels) if l not in scatter_labels]
    line_labels = [l for l in labels if l not in scatter_labels]

    # Combine proxy scatter handles with line handles
    ax.legend(handles=proxy_scatters + line_handles,
              labels=[p.get_label() for p in proxy_scatters] + line_labels,
              loc=loc, **kwargs)

def get_trend_labels(method: str, k: float, p_low=None, p_high=None):
    """
    Return upper and lower labels for the trend based on method.

    Parameters
    ----------
    method : str
        One of "sigma", "iqr", "percentile".
    k : float
        Scaling factor for the bounds.

    Returns
    -------
    upper_label : str
    lower_label : str
    """
    if method == "sigma":
        upper_label = rf"Upper: y = f(x)+{k}·σ(x)"
        lower_label = rf"Lower: y = f(x)-{k}·σ(x)"

    elif method == "iqr":
        upper_label = f"Upper: y = f(x) +Q3+(k-1)·IQR"
        lower_label = f"Lower: y = f(x) +Q1-(k-1)·IQR\n(k={k})"

    elif method == "percentile":
        upper_label = f"Upper limit:\ny = f(x)+Ph+(k-1)·ΔP"
        lower_label = f"Lower limit:\ny = f(x)+Pl-(k-1)·ΔP\n(k={k}, ΔP=Ph-Pl\nPh={p_high},Pl={p_low})"

    else:
        raise ValueError("method must be 'sigma', 'iqr', or 'percentile'")

    return upper_label, lower_label

def plot_travel_time_qc_core(
    ax,
    df,
    distance_col,
    tt_col,
    d_trend,
    t_trend,
    f_trend,
    bins,
    compute_bounds_func,
    k,
    method,
    p_low=None,
    p_high=None,
    show_bins=True,
    show_boundaries=True,
    x_limits=None
):
    """
    Core plotting logic (reusable anywhere).
    """

    inside = df["inside_bounds"]
    outside = ~inside

    # print(df)
    # exit()

    d_all = df[distance_col].values
    t_all = df[tt_col].values

    # Scatter
    ax.scatter(d_all[outside], t_all[outside], s=2, alpha=0.6,
                color="red",label="Outside bounds")
    ax.scatter(d_all[inside], t_all[inside], s=2, alpha=0.6, 
               color="black", label="Inside bounds")

    # Trend
    ax.plot(d_trend, t_trend, "b-", lw=3, label="Median trend")

    # Use bin centers for plotting instead of uniform linspace
    if bins is not None:
        d_plot = bins[:-1] + np.diff(bins) / 2
        if x_limits is not None:
            d_plot = d_plot[d_plot <= x_limits[1]]
    else:
        d_plot = np.linspace(d_all.min(), d_all.max(), 1000)


    # Bins
    if bins is not None:
        if x_limits is not None:
            x_max_plot = x_limits[1]
        else:
            x_max_plot = d_all.max()

        centers = bins[:-1] + np.diff(bins) / 2
        centers = centers[centers <= x_max_plot] 
        centers = np.concatenate([centers, np.array([x_max_plot])])  # Ensure we include the max limit as a center for plotting
         

        if show_bins:
            for c in centers:
                ax.axvline(c, color="black", linestyle="--", linewidth=0.5, alpha=0.2)

    else:
        centers = np.linspace(d_all.min(), d_all.max(), 1000)

    ax.plot(centers, f_trend(centers), "g-", lw=2, label="Interpolated trend")

    # Bounds
    _, lower, upper = compute_bounds_func(centers, k=k)

    upper_label, lower_label = get_trend_labels(method, k, p_low=p_low, p_high=p_high)

    if show_boundaries:
        ax.plot(centers, upper, color="orange", lw=1.5, label=upper_label)
        ax.plot(centers, lower, color="orange", lw=1.5, label=lower_label)

    return ax


def plot_travel_time_qc(
    df,
    distance_col,
    tt_col,
    d_trend,
    t_trend,
    f_trend,
    bins,
    compute_bounds_func,
    k=20,
    method="sigma",
    p_low=None,
    p_high=None,
    show_bins=True,
    show_boundaries=True,
    x_limits=None,
    y_limits=None,
    figsize=(10, 6),
    title=None,
    savepath=None,
    add_inset=True,
    inset_xlim=(0, 15),
    inset_ylim=(0, 50)
):
    """
    Standalone Travel Time QC plotting function (main + inset).
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns distance_col, tt_col, inside_bounds
    distance_col, tt_col : str
        Column names for distance and travel time
    d_trend, t_trend : array-like
        Trend points (binned median)
    f_trend : callable
        Interpolation function for trend
    bins : array-like
        Bin edges for plotting vertical lines
    compute_bounds_func : callable
        Function to compute bounds: f(x, k)
    k : float
        Sigma or percentile multiplier
    add_inset : bool
        If True, add zoomed inset
    inset_xlim, inset_ylim : tuple
        Limits for inset axes
    """
    
    if "inside_bounds" not in df.columns:
        raise ValueError("DataFrame must contain 'inside_bounds' column")
    
    fig, ax = plt.subplots(figsize=figsize)

    # ---- MAIN PLOT ----
    plot_travel_time_qc_core(
        ax=ax,
        df=df,
        distance_col=distance_col,
        tt_col=tt_col,
        d_trend=d_trend,
        t_trend=t_trend,
        f_trend=f_trend,
        bins=bins,
        compute_bounds_func=compute_bounds_func,
        k=k,
        p_low=p_low,
        p_high=p_high,
        method=method,
        show_bins=show_bins,
        show_boundaries=show_boundaries,
        x_limits=x_limits
    )

    # ax.legend(loc="upper left")
    customize_legend(ax, loc="upper left")

    # ---- INSET PLOT ----
    if add_inset:
        axins = inset_axes(ax, width="35%", height="35%", loc="lower right", borderpad=2)

        plot_travel_time_qc_core(
            ax=axins,
            df=df,
            distance_col=distance_col,
            tt_col=tt_col,
            d_trend=d_trend,
            t_trend=t_trend,
            f_trend=f_trend,
            bins=bins,
            compute_bounds_func=compute_bounds_func,
            k=k,
            method=method,
            show_bins=show_bins,
            show_boundaries=show_boundaries,
            x_limits=inset_xlim
        )

        tune_zoomed_travel_time_qc(
            axins,
            xlim=inset_xlim,
            ylim=inset_ylim
        )

        # Draw lines (brackets) connecting inset to zoomed region
        mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.5", lw=1.2)

    # ---- AXES LABELS & Limits ----
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Travel Time (s)")

    if title:
        ax.set_title(title)
    
    if x_limits is not None:
        ax.set_xlim(*x_limits)
    if y_limits is not None:
        ax.set_ylim(*y_limits)

    # 3 minor ticks between each major tick
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))  # 5 = 4 minors between majors
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))

    ax.grid(True, which="both", axis="y",
            linestyle="--", linewidth=0.5, alpha=0.3)

    plt.tight_layout()

    if savepath is not None:
        plt.savefig(savepath, dpi=300)
        print(f"Saved plot to {savepath}")

    return fig, ax

def plot_all_phases_qc(
    qc_dict,
    distance_col,
    tt_col,
    compute_bounds_funcs,
    k_dict,
    method_dict,
    p_bounds_dict=None,
    figsize=(12, 8),
    phase_order=("P", "Pn", "Pg", "S", "Sn", "Sg"),
    add_inset=True,
    inset_limits=None,
    savepath=None
):
    """
    Plot QC for multiple phases using precomputed TravelTimeQC objects.

    Parameters
    ----------
    qc_dict : dict
        {phase: TravelTimeQC instance}
    compute_bounds_funcs : dict
        {phase: function}
    k_dict : dict
        {phase: k value}
    method_dict : dict
        {phase: method string}
    p_bounds_dict : dict
        {phase: (p_low, p_high)} or None
    """

    import matplotlib.pyplot as plt
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

    fig, axes = plt.subplots(2, 3, figsize=figsize)
    axes = axes.flatten()

    for idx, phase in enumerate(phase_order):
        ax = axes[idx]

        qc = qc_dict.get(phase, None)
        if qc is None:
            ax.set_title(f"{phase} (no data)")
            ax.axis("off")
            continue

        df = qc.df

        compute_bounds_func = compute_bounds_funcs[phase]
        k = k_dict[phase]
        method = method_dict[phase]

        if p_bounds_dict:
            p_low, p_high = p_bounds_dict.get(phase, (None, None))
        else:
            p_low, p_high = None, None

        # ---- MAIN PLOT ----
        plot_travel_time_qc_core(
            ax=ax,
            df=df,
            distance_col=distance_col,
            tt_col=tt_col,
            d_trend=qc.d_trend,
            t_trend=qc.t_trend,
            f_trend=qc.f_trend,
            bins=qc.bins,
            compute_bounds_func=compute_bounds_func,
            k=k,
            method=method,
            p_low=p_low,
            p_high=p_high,
            show_bins=True,
            show_boundaries=True,
            x_limits=None
        )

        customize_legend(ax, loc="upper left")

        ax.set_title(phase)

        # ---- INSET ----
        if add_inset:
            xlim = (0, 30)
            ylim = (0, 10)

            if inset_limits and phase in inset_limits:
                xlim = inset_limits[phase].get("x", xlim)
                ylim = inset_limits[phase].get("y", ylim)

            axins = inset_axes(ax, width="35%", height="35%", loc="lower right")

            plot_travel_time_qc_core(
                ax=axins,
                df=df,
                distance_col=distance_col,
                tt_col=tt_col,
                d_trend=qc.d_trend,
                t_trend=qc.t_trend,
                f_trend=qc.f_trend,
                bins=qc.bins,
                compute_bounds_func=compute_bounds_func,
                k=k,
                method=method,
                p_low=p_low,
                p_high=p_high,
                show_bins=True,
                show_boundaries=True,
                x_limits=xlim
            )

            tune_zoomed_travel_time_qc(axins, xlim=xlim, ylim=ylim)
            mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.5")

        # ---- CLEAN AXES ----
        if idx % 3 != 0:
            ax.set_ylabel("")
        if idx < 3:
            ax.set_xlabel("")

    fig.tight_layout()

    if savepath:
        fig.savefig(savepath, dpi=300)
        print(f"Saved to {savepath}")

    return fig, axes