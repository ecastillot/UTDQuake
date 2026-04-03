# qc_travel_time.py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.interpolate import interp1d


class TravelTimeModel:
    def __init__(self, model_df: pd.DataFrame):
        self.model_df = model_df.sort_values("distance_center")

        self._build_interpolators()

    def _build_interpolators(self):
        x = self.model_df["distance_center"].values

        self.std_func = interp1d(x, self.model_df["QC_std"], 
                                 fill_value="extrapolate", bounds_error=False)

        self.p_funcs = {}
        for col in self.model_df.columns:
            if "QC_tt_residual_p" in col:
                self.p_funcs[col] = interp1d(
                    x, self.model_df[col],
                    fill_value="extrapolate", bounds_error=False
                )

class TravelTimeQC:
    """
    Class for Travel Time Quality Control using trend and sigma filtering.
    """

    def __init__(self, df: pd.DataFrame, distance_col: str, tt_col: str, phase: str):
        self.df = df[df["phase"] == phase].copy().dropna(subset=[distance_col, tt_col])
        self.distance_col = distance_col
        self.tt_col = tt_col



        #add zero in the beggining
        self.d = self.df[distance_col].values
        self.t = self.df[tt_col].values

        self.d_clean = self.d
        self.t_clean = self.t 
        self.d_trend = None
        self.t_trend = None
        self.f_trend = None
        self.sigma_function = None
        self.upper = None
        self.lower = None
        self.k = None
        self.bins = None
        self.method = None
        self.p_low = None
        self.p_high = None
        self.percentile_method = False
        self.y_pred = None
        self.df_cleaned = None  # DataFrame with residuals and sigma multiples


    @staticmethod
    def remove_xy_outliers_mahalanobis(x: np.ndarray, y: np.ndarray, 
                                       threshold: float = 3) -> np.ndarray:
        """
        Return boolean mask of points that are NOT Mahalanobis outliers.
        """
        xy = np.vstack([x, y]).T
        cov = np.cov(xy, rowvar=False)
        mean = np.mean(xy, axis=0)
        diff = xy - mean
        inv_cov = np.linalg.pinv(cov)
        md = np.sqrt(np.sum(diff @ inv_cov * diff, axis=1))
        return md <= threshold

    def clean_data(self):
        mask = self.remove_xy_outliers_mahalanobis(self.d, self.t)
        self.d_clean = self.d[mask]
        self.t_clean = self.t[mask]

       

    def build_bins(self, n_bins=100, dmin=None, dmax=None):
        """
        Build log-spaced bins for consistent trend and sigma estimation.
        """
        
        if dmin is None:
            dmin = max(1e-3, self.d_clean.min())
        else:
            if dmin < 1e-3:
                raise ValueError("dmin must be >= 1e-3 to avoid log(0) issues.")
        if dmax is None:
            dmax = self.d_clean.max()

        bins = np.logspace(np.log10(dmin), np.log10(dmax), n_bins)

        self.bins = bins
        return bins

    def compute_binned_trend(self, bins, min_points_per_bin=5):

        bin_med, _, _ = stats.binned_statistic(
            self.d_clean, self.t_clean,
            statistic="median",
            bins=bins
        )

        bin_count, _ = np.histogram(self.d_clean, bins=bins)

        d_centers = bins[:-1] + np.diff(bins) / 2

        valid = bin_count >= min_points_per_bin

        d_trend = d_centers[valid]
        t_trend = bin_med[valid]

        # ---- 🔥 FORCE ORIGIN ----
        if len(d_trend) == 0:
            raise ValueError("No valid bins to compute trend.")

        # Only add if not already near zero
        if d_trend[0] > 0:
            d_trend = np.insert(d_trend, 0, 0.0)
            t_trend = np.insert(t_trend, 0, 0.0)

        self.d_trend = d_trend
        self.t_trend = t_trend

    def compute_percentile_function(self, bins, p_low=25, p_high=75, min_points_per_bin=5):
        """
        Compute percentile-based spread as function of distance.
        
        Parameters
        ----------
        p_low : float
            Lower percentile (e.g., 25 for IQR)
        p_high : float
            Upper percentile (e.g., 75 for IQR)
        """
        self.p_low = p_low
        self.p_high = p_high
        self.percentile_method = True  # flag
        residuals = self.t_clean - self.f_trend(self.d_clean)

        centers = bins[:-1] + np.diff(bins) / 2

        low_list = []
        high_list = []

        for i in range(len(bins) - 1):
            mask = (self.d_clean >= bins[i]) & (self.d_clean < bins[i+1])

            if np.sum(mask) >= min_points_per_bin:
                r = residuals[mask]
                low = np.percentile(r, p_low)
                high = np.percentile(r, p_high)
            else:
                low, high = np.nan, np.nan

            low_list.append(low)
            high_list.append(high)

        low_arr = np.array(low_list)
        high_arr = np.array(high_list)

        valid = ~np.isnan(low_arr) & ~np.isnan(high_arr)

        if np.sum(valid) < 2:
            # fallback global
            r = residuals
            low_global = np.percentile(r, p_low)
            high_global = np.percentile(r, p_high)

            self.low_function = lambda xx: np.full_like(xx, low_global)
            self.high_function = lambda xx: np.full_like(xx, high_global)
        else:
            self.low_function = lambda xx: np.interp(xx, centers[valid], low_arr[valid])
            self.high_function = lambda xx: np.interp(xx, centers[valid], high_arr[valid])

    def compute_percentile_bounds(self, x: np.ndarray, k: float = 1.0):
        """
        Compute bounds using percentile envelopes.

        k = 1 → raw percentiles
        k > 1 → expand envelope
        """
        y_pred = self.f_trend(x)

        low = self.low_function(x)
        high = self.high_function(x)

        spread = high - low

        lower = y_pred + low - (k - 1) * spread
        upper = y_pred + high + (k - 1) * spread

        return y_pred, lower, upper

    def compute_iqr_function(self, bins, min_points_per_bin=5):
        self.compute_percentile_function(
            bins,
            p_low=25,
            p_high=75,
            min_points_per_bin=min_points_per_bin
        )

    def interpolate_trend(self, kind: str = "linear", fill_value: str = "extrapolate"):
        """
        Create interpolation function for trend.
        """
        if self.d_trend is None or len(self.d_trend) == 0:
            raise ValueError("Trend not computed yet.")

        sort_idx = np.argsort(self.d_trend)
        self.f_trend = interp1d(
            self.d_trend[sort_idx],
            self.t_trend[sort_idx],
            kind=kind,
            fill_value=fill_value,
            bounds_error=False  
        )

    def compute_sigma_function(self, bins, min_points_per_bin=5):

        residuals = self.t_clean - self.f_trend(self.d_clean)

        centers = bins[:-1] + np.diff(bins) / 2
        sigmas = []

        for i in range(len(bins) - 1):
            mask = (self.d_clean >= bins[i]) & (self.d_clean < bins[i+1])

            if np.sum(mask) >= min_points_per_bin:
                r = residuals[mask]
                sigma = 1.4826 * np.median(np.abs(r - np.median(r)))
            else:
                sigma = np.nan

            sigmas.append(sigma)

        sigmas = np.array(sigmas)
        valid = ~np.isnan(sigmas)

        if np.sum(valid) < 2:
            global_sigma = 1.4826 * np.median(np.abs(residuals - np.median(residuals)))
            self.sigma_function = lambda xx: np.full_like(xx, global_sigma)
        else:
            self.sigma_function = lambda xx: np.interp(xx, centers[valid], sigmas[valid])

    def compute_sigma_bounds(self, x: np.ndarray, k: float = 3.0):
        """
        Compute prediction and bounds at given x.
        """
        y_pred = self.f_trend(x)
        sigma_x = self.sigma_function(x)

        upper = y_pred + k * sigma_x
        lower = y_pred - k * sigma_x

        return y_pred, lower, upper

    def annotate_residuals(self, k: float = 3.0, method="sigma"):
        self.k = k
        self.method = method

        x = self.df[self.distance_col].values
        y = self.df[self.tt_col].values

        if method == "sigma":
            y_pred, lower, upper = self.compute_sigma_bounds(x, k=k)
        
        elif method == "percentile":
            y_pred, lower, upper = self.compute_percentile_bounds(x, k=k)
        elif method == "iqr":
            y_pred, lower, upper = self.compute_percentile_bounds(x, k=k)
        else:
            raise ValueError("method must be 'sigma' or 'iqr'")

        residuals = y - y_pred

        self.df["y_pred"] = y_pred
        self.df["residual"] = residuals
        self.df["upper_bound"] = upper
        self.df["lower_bound"] = lower

        self.df["inside_bounds"] = (y >= lower) & (y <= upper)

        # self.df_cleaned = self.df[self.df["inside_bounds"]].copy()

        return self.df

    def export_statistical_model(self, bins, min_points_per_bin=5, filepath=None):
        """
        Export statistical travel-time model using percentiles only.
        P50 acts as the central trend.
        """

        if self.f_trend is None:
            raise ValueError("Run interpolate_trend() first.")

        # Residuals
        residuals = self.t_clean - self.f_trend(self.d_clean)

        centers = bins[:-1] + np.diff(bins) / 2

        stats_list = []

        for i in range(len(bins) - 1):
            mask = (self.d_clean >= bins[i]) & (self.d_clean < bins[i+1])

            if np.sum(mask) >= min_points_per_bin:
                r = residuals[mask]

                # Percentiles of residuals
                p1  = np.percentile(r, 1)
                p5  = np.percentile(r, 5)
                p25 = np.percentile(r, 25)
                p50 = np.percentile(r, 50)
                p75 = np.percentile(r, 75)
                p95 = np.percentile(r, 95)
                p99 = np.percentile(r, 99)

                sigma = 1.4826 * np.median(np.abs(r - np.median(r)))

                trend_val = self.f_trend(centers[i])

                stats_list.append({
                    "distance": centers[i],
                    "sigma": sigma,
                    "P1":  trend_val + p1,
                    "P5":  trend_val + p5,
                    "P25": trend_val + p25,
                    "P50": trend_val + p50,  # central trend
                    "P75": trend_val + p75,
                    "P95": trend_val + p95,
                    "P99": trend_val + p99,
                    "count": np.sum(mask)
                })

        df_stats = pd.DataFrame(stats_list)

        # Add origin (0,0)
        if len(df_stats) > 0 and df_stats["distance"].iloc[0] > 0:
            zero_row = {
                "distance": 0.0,
                "sigma": 0.0,
                "P1": 0.0,
                "P5": 0.0,
                "P25": 0.0,
                "P50": 0.0,
                "P75": 0.0,
                "P95": 0.0,
                "P99": 0.0,
                "count": 0
            }
            df_stats = pd.concat([pd.DataFrame([zero_row]), df_stats], ignore_index=True)

        if filepath:
            if filepath.endswith(".csv"):
                df_stats.to_csv(filepath, index=False)
            elif filepath.endswith(".parquet"):
                df_stats.to_parquet(filepath, index=False)
            else:
                raise ValueError("Unsupported format.")

        return df_stats

    

    def plot(self,k=20, 
             method="sigma",
             show_bins=True,
             show_boundaries=True,
             x_limits=None, y_limits=None, 
             figsize=(10, 6), title=None,
             savepath=None):
        """
        Plot travel time QC figure with inside/outside classification.
        """
        if "inside_bounds" not in self.df.columns:
            raise ValueError("Run annotate_residuals() before plotting.")

        fig, ax = plt.subplots(figsize=figsize)

        # Masks
        inside = self.df["inside_bounds"]
        outside = ~inside

        d_all = self.df[self.distance_col].values
        t_all = self.df[self.tt_col].values

        # Plot outside (bad) points
        ax.scatter(
            d_all[outside], t_all[outside],
            s=2, alpha=0.6, color="red", label="Outside 3σ"
        )

        # Plot inside (good) points
        ax.scatter(
            d_all[inside], t_all[inside],
            s=2, alpha=0.6, color="black", label="Inside 3σ"
        )

        # Trend (binned median)
        ax.plot(self.d_trend, self.t_trend, "b-", lw=3, label="Median trend")

        # Interpolated trend
        d_plot = np.linspace(self.d.min(), self.d.max(), 500)
        ax.plot(d_plot, self.f_trend(d_plot), "g-", lw=2, label="f(x): Interpolated trend")

        # Bounds
        # print(self.upper,self.lower)
        if method == "sigma":
            _, lower, upper = self.compute_sigma_bounds(d_plot, k=k)

            upper_label = rf"Upper: y = f(x) + {k}·σ(x)"
            lower_label = rf"Lower: y = f(x) - {k}·σ(x)"

        elif method == "iqr":
            _, lower, upper = self.compute_percentile_bounds(d_plot, k=k)

            upper_label = rf"Upper: y = f(x) + Q3 + (k-1)·IQR (k={k})"
            lower_label = rf"Lower: y = f(x) + Q1 - (k-1)·IQR (k={k})"

        elif method == "percentile":
            _, lower, upper = self.compute_percentile_bounds(d_plot, k=k)

            p_low = getattr(self, "p_low", "?")
            p_high = getattr(self, "p_high", "?")

            upper_label = (
                rf"Upper: y = f(x) + P{p_high} + (k-1)·ΔP"
                rf"  (k={k})"
            )
            lower_label = (
                rf"Lower: y = f(x) + P{p_low} - (k-1)·ΔP"
                rf"  (k={k})"
            )
        else:
            raise ValueError("method must be 'sigma', 'iqr', or 'percentile'")


        if show_boundaries:
            ax.plot(d_plot, upper, color="orange", lw=1.5, label=upper_label)
            ax.plot(d_plot, lower, color="orange", lw=1.5, label=lower_label)

        if show_bins:
            if x_limits is not None:
                x_max_plot = x_limits[1]
            else:
                x_max_plot = np.nanmax(self.df[self.distance_col].values)

            # Use bin centers (cleaner)
            centers = self.bins[:-1] + np.diff(self.bins) / 2

            # Keep only bins within plotted range
            centers = centers[centers <= x_max_plot]

            for c in centers:
                ax.axvline(c, color="black", linestyle="--", linewidth=0.5, alpha=0.2)


        # Limits
        if x_limits is not None:
            ax.set_xlim(*x_limits)
        if y_limits is not None:
            ax.set_ylim(*y_limits)

        ax.set_xlabel("Distance (km)")
        ax.set_ylabel("Travel Time (s)")
        ax.legend()
        if title:
            ax.set_title(title)


        # grid only in the x axis
        ax.grid(True, which="both", axis="y", 
                linestyle="--", linewidth=0.5, 
                alpha=0.3)

        plt.tight_layout()
        if savepath is not None:
            plt.savefig(savepath,dpi=300)
            print(f"Saved plot to {savepath}")
        return fig, ax

if __name__ == "__main__":
    import pandas as pd
    import os

    network = "us"

    df = pd.read_parquet(f"/groups/igonin/ecastillo/UTDQuake/picks/network={network}.parquet")
    qc = TravelTimeQC(df, distance_col="linear_hyp_distance", tt_col="travel_time", phase="P")
    # qc.clean_data()
    bins = qc.build_bins( dmin=0.001, dmax=40e3, n_bins=100)
    # bins = qc.build_bins(n_bins=100, dmin=1, dmax=40e3)
    qc.compute_binned_trend(bins)
    qc.interpolate_trend()
    # qc.compute_sigma_function(bins)
    qc.compute_percentile_function(bins, p_low=0.1, p_high=99.5)
    

    k = 1.1

    # # Compute bounds for plotting
    # d_plot = np.linspace(qc.d.min(), qc.d.max(), 500)
    # qc.compute_bounds(d_plot, k=k)

    # Annotate residuals & sigma multiples in the DataFrame
    df_with_residuals = qc.annotate_residuals(k=k, method="percentile")

    qc.export_statistical_model(bins, min_points_per_bin=5, 
    # filepath=f"/groups/igonin/ecastillo/UTDQuake/picks/network={network}_travel_time_model.csv"
    filepath=f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/nets/test.csv"
    )

    # df_with_residuals now has:
    # - residual: t_actual - t_trend
    # - sigma_multiple: residual / sigma
    # - inside_bounds: True/False
    print(df_with_residuals.head())

    # # Plot results
    # save_path = f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/nets/{network}.png"
    # os.makedirs(os.path.dirname(save_path), exist_ok=True)
    # qc.plot(
    #     # x_limits=(0, 12000),
    #     #  y_limits=(0, 100),
    #     k=k,
    #     method="percentile",
    #          title="P-phase QC with Residuals",
    #         savepath=save_path)