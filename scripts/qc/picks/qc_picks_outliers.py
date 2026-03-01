import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def remove_super_outliers(x, y, lower_percentile=0.5, upper_percentile=99.5):
    x = np.array(x)
    y = np.array(y)
    
    # Compute percentiles
    x_min, x_max = np.percentile(x, [lower_percentile, upper_percentile])
    y_min, y_max = np.percentile(y, [lower_percentile, upper_percentile])
    
    # Mask points within percentiles
    mask = (x >= x_min) & (x <= x_max) & (y >= y_min) & (y <= y_max)
    
    return x[mask], y[mask]

df = pd.read_parquet("/groups/igonin/ecastillo/UTDQuake/picks/network=ISC.parquet")
save_path = "/groups/igonin/ecastillo/utdquake/scripts/qc/picks/qc_picks.png"

phase_order = ["P", "Pn", "Pg",
               "S", "Sn", "Sg"]
columns = ["travel_time", "linear_hyp_distance", "phase"]
min_points = 20

k = {"P": (5,10), 
     "Pn": (5,10), 
     "Pg": (5,10), 
     "S": (5,10), 
     "Sn": (5,10),  
     "Sg": (5,10)}

df_original = df.copy()
original_counts = (
    df_original["phase"]
    .value_counts()
    .reindex(phase_order, fill_value=0)
)

df = df[columns]
print(df.isna().sum())  # count NaNs before dropping
df = df.dropna(subset=columns)

df = df[df["phase"].isin(phase_order)]

fig, axes = plt.subplots(
    2,
    3,
    figsize=(8, 12),
    # sharey="row"
)

fig.subplots_adjust(
    # hspace=0.4,  # vertical spacing
    wspace=0.5   # horizontal spacing
)

for ax, phase in zip(axes.flatten(), phase_order):

    if len(df[df["phase"] == phase]) == 0:
        ax.set_title(phase)
        continue


    df_phase = df[df["phase"] == phase]
    # print(phase, df_phase["travel_time"].min(), df_phase["travel_time"].max())
    # print(phase, df_phase["linear_hyp_distance"].min(), df_phase["linear_hyp_distance"].max())
    # print(phase, df_phase.isna().sum())  # count NaNs

    x = df_phase["travel_time"].values
    y = df_phase["linear_hyp_distance"].values


    #remove outliers in x and y
    x, y = remove_super_outliers(x, y)

    ax.scatter(
        x,
        y,
        s=4,
        color="black",
        alpha=1,
    )

    if len(x) < min_points or len(y) < min_points:
        ax.set_title(phase)
        continue

    # 2nd-degree polynomial fit
    coeffs = np.polyfit(x, y, 2)  # returns [a, b, c] for ax^2 + bx + c
    poly = np.poly1d(coeffs)

    # Create smooth x-values for the curve
    x_fit = np.linspace(x.min(), x.max(), 200)
    y_fit = poly(x_fit)

    print(f"{phase} fit coefficients: {coeffs}")
    print(len(x), len(y))

    # Plot polynomial regression
    a, b, c = coeffs
    # eq_label = "fit"
    if abs(a) < 1e-4:
        eq_label = r"$y = {:.2f}x {:+.2f}$".format(b, c)
    else:
        eq_label = r"$y = {:.2f}x^2 {:+.2f}x {:+.2f}$".format(a, b, c)
    ax.plot(x_fit, y_fit, color="red", 
            lw=2, label=eq_label)
    


    y_pred = poly(x)
    residuals = y - y_pred
    sigma = np.std(residuals)


    # Residual statistics
    y_pred = poly(x)
    residuals = y - y_pred
    sigma = np.std(residuals)

    # ----- Variable k as function of travel time -----
    k_min, k_max = k[phase]     # strict at beginning

    # Normalize x_fit between 0 and 1
    x_norm = (x_fit - x_fit.min()) / (x_fit.max() - x_fit.min())

    # k varies smoothly
    k_variable = k_min + (k_max - k_min) * x_norm

    # Bounds now depend on x
    upper_fit = y_fit + k_variable * sigma
    lower_fit = y_fit - k_variable * sigma

    # Plot bounds
    upper_label = r"$f(x) + k(x)\sigma$"
    lower_label = r"$f(x) - k(x)\sigma$"
    ax.plot(x_fit, upper_fit, color="blue", linestyle="--", 
            linewidth=1,
            # label=upper_label
            )
    ax.plot(x_fit, lower_fit, color="blue", linestyle="--",
             linewidth=1,
            # label=lower_label
            )

    # Get axis limits AFTER scatter
    ymin, ymax = ax.get_ylim()

    # Shade outside region
    ax.fill_between(x_fit, ymin, lower_fit, color="gray", alpha=0.2)
    ax.fill_between(x_fit, upper_fit, ymax, color="gray", alpha=0.2)

    original_n = original_counts[phase]
    current_n = len(x)

    removed_n = original_n - current_n
    removed_pct = 100 * removed_n / original_n if original_n > 0 else 0

    ax.text(
        0.02, 0.98,
        f"Original: {original_n}\n"
        f"Kept: {current_n}\n"
        f"Removed: {removed_n} ({removed_pct:.1f}%)",
        transform=ax.transAxes,
        verticalalignment="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
    )

    ax.text(
        0.02, 0.02,
        eq_label,
        transform=ax.transAxes,
        fontsize=8,
        color="red",
        
    )

    # ax.legend(loc="lower left")
    ax.set_title(phase)
    ax.set_xlabel("Travel Time")
    ax.set_ylabel("Hyp. Distance")

fig.tight_layout()
fig.savefig(save_path, dpi=300)