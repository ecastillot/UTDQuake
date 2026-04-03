import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_sigma_score(df, model,
                        distance_col="linear_hyp_distance",
                        tt_col="travel_time"):
    
    df = df.copy()
    
    # Model bins
    c_bins = model["distance_center"].values
    median = model["tt_p50"].values
    sigma = model["sigma"].values
    
    x = df[distance_col].values
    y = df[tt_col].values
    
    # Interpolate model values at each x
    mu = np.interp(x, c_bins, median)
    sig = np.interp(x, c_bins, sigma)
    
    # Avoid division by zero
    sig = np.where(sig == 0, np.nan, sig)
    
    # Z-score (sigma distance)
    z = (y - mu) / sig
    
    df["tt_residual"] = y - mu
    df["tt_sigma"] = sig
    df["tt_zscore"] = z
    df["tt_abs_zscore"] = np.abs(z)
    
    return df


def quick_tt_sigma_binary_plot(df,
                            distance_col="linear_hyp_distance",
                            tt_col="travel_time",
                            z_col="travel_time_zscore",
                            phase=None,
                            threshold=3):
    
    if phase is not None:
        df = df[df["phase"] == phase]
    
    df = df.dropna(subset=[distance_col, tt_col, z_col])
    
    x = df[distance_col].values
    y = df[tt_col].values
    z = df[z_col].values
    
    inside = z <= threshold
    outside = z > threshold
    
    fig, ax = plt.subplots(figsize=(6,4))
    
    ax.scatter(x[outside], y[outside],
               s=6, alpha=0.9,
               label=f"> {threshold}σ")
    ax.scatter(x[inside], y[inside],
               s=4, alpha=0.6,
               label=f"≤ {threshold}σ")
    
    
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Travel Time (s)")
    
    title = f"Travel Time QC (Phase: {phase})" if phase else "Travel Time QC"
    ax.set_title(title)
    
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend()

    path = "/groups/igonin/ecastillo/utdquake/scripts/qc/picks/compute_sigma_Score.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    
    return fig, ax

network = "RSNC"
# data = pd.read_parquet(f"/groups/igonin/ecastillo/UTDQuake/picks/network={network}.parquet")
# model = pd.read_csv(f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/results/qc/network={network}.csv")
# computed = compute_sigma_score(data, model)
computed = pd.read_parquet(f"/groups/igonin/ecastillo/UTDQuake/manifests/qc/picks/network={network}.parquet")

# print(computed[["linear_hyp_distance", "travel_time", "tt_residual", "tt_sigma", "tt_zscore", "tt_abs_zscore"]].head())

fig, ax = quick_tt_sigma_binary_plot(computed, phase="P", threshold=2)