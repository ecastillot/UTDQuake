"""
Modular seismic phase trend modeling and filtering.
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from dataclasses import dataclass, field
from typing import Dict, List
from .config import GLOBAL_TRENDS_DEFAULTS_DEG2
from .log import QCLog

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class PhaseTrendConfig:
    phase_order: List[str] = field(default_factory=lambda: ["P", "Pn", "Pg", "S", "Sn", "Sg"])
    k_dict: Dict[str, float] = field(default_factory=lambda: {
        "P": 3, "Pn": 3, "Pg": 3, "S": 3, "Sn": 3, "Sg": 3
    })
    min_points: int = 20
    degree: int = 2
    fit_method: str = "polyfit"

    def for_phase(self, phase: str) -> "PhaseTrendConfig":
        if phase not in self.phase_order:
            raise ValueError(f"Phase '{phase}' not found in configuration.")

        return PhaseTrendConfig(
            phase_order=[phase],
            k_dict={phase: self.k_dict[phase]},
            min_points=self.min_points,
            degree=self.degree,
            fit_method=self.fit_method
        )


class GlobalTrendFilter:
    """
    Apply a global (network-level) trend gate to seismic picks.

    Acts as a PRIOR filter before local adaptive modeling.
    """

    def __init__(self, global_trends=None):

        self.global_trends = global_trends or GLOBAL_TRENDS_DEFAULTS_DEG2

        # Compile and save models
        self.models: Dict[str, dict] = {}

        for phase, info in self.global_trends.items():
            poly = np.poly1d(info["coefficients"])
            sigma = info.get("sigma_max", info.get("sigma_median"))
            k = info.get("k", 5)

            self.models[phase] = {
                "poly": poly,
                "coefficients": info["coefficients"],
                "sigma_median": info.get("sigma_median"),
                "sigma_max": info.get("sigma_max"),
                "sigma": sigma,
                "degree": info.get("degree", 1),
                "k": k,
                "x_min": info.get("x_min"),
                "x_max": info.get("x_max")
            }


    def to_dict(self):
        data = {}

        for phase, model in self.models.items():

            data[phase] = {
                "coefficients": model["coefficients"],
                "sigma_median": model["sigma_median"],
                "sigma_max": model["sigma_max"],
                "k": model["k"],
                "degree": model["degree"],
                "x_min": model["x_min"],
                "x_max": model["x_max"]
            }

        return data
    

    def to_json(self, filepath):

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4)    


    @classmethod
    def from_json(cls, filepath):

        with open(filepath) as f:
            trends = json.load(f)

        return cls(global_trends=trends)

    # --------------------------------------------------
    # 1️⃣ Compute bounds for ONE phase (for plotting)
    # --------------------------------------------------
    def compute_bounds(self, x, phase):
        """
        Compute global prediction and bounds for a given phase.

        Returns
        -------
        y_pred, lower, upper
        """

        if phase not in self.models:
            return None, None, None

        model = self.models[phase]

        y_pred = model["poly"](x)
        upper = y_pred + model["k"] * model["sigma"]
        lower = y_pred - model["k"] * model["sigma"]

        return y_pred, lower, upper


    # --------------------------------------------------
    # 2️⃣ Apply filtering over ALL phases in dataframe
    # --------------------------------------------------
    def apply(self,
              df,
              phase_col="phase",
              x_col="linear_hyp_distance",
              y_col="travel_time",
              log=None,
              debug=True):
        """
        Apply global trend filter to all phases and log removals.

        Returns
        -------
        kept_df : pd.DataFrame
            Picks within global bounds
        removed_df : pd.DataFrame
            Picks outside global bounds
        """

        if log is None:
            log = QCLog()

        original_total = len(df)
        kept_list = []
        removed_list = []

        # Loop over phases that have global trends
        for phase, model in self.models.items():
            df_phase = df[df[phase_col] == phase]

            #add zero bounds to avoid negative distances or times, which can cause issues with the model
            zero_row = {x_col: 0, y_col: 0, phase_col: phase}
            for col in df_phase.columns:
                if col not in zero_row:
                    zero_row[col] = np.nan
            df_phase = pd.concat([pd.DataFrame([zero_row]), df_phase], ignore_index=True)

            df_phase = df_phase[df_phase[x_col]>=0]
            df_phase = df_phase[df_phase[y_col]>=0]
            
            if df_phase.empty:
                continue

            x = df_phase[x_col].values
            y = df_phase[y_col].values

            y_pred, lower, upper = self.compute_bounds(x, phase)

            lower = np.maximum(lower, 0)

            mask = (y >= lower) & (y <= upper)


            kept = df_phase[mask].copy()
            removed = df_phase[~mask].copy()

            # Optionally store bounds for plotting
            kept["lower_bound"] = lower[mask]
            kept["upper_bound"] = upper[mask]
            removed["lower_bound"] = lower[~mask]
            removed["upper_bound"] = upper[~mask]

            kept_list.append(kept)
            removed_list.append(removed)

            # Logging
            step_removed = len(removed)
            log.add_step(f"global_trend_{phase}",
                            step_removed,
                            thresholds={"k*sigma": model["k"]*model["sigma"]},
                            phase=phase)
            if debug:
                print(f"[GlobalTrend] Phase {phase}: removed {step_removed} "
                    f"(Phase cumulative: {log.cumulative_per_phase[phase]}/{len(df[df['phase']==phase])})")

        # Include phases without global trends as kept
        other_phases = df[~df[phase_col].isin(self.models.keys())]
        if not other_phases.empty:
            kept_list.append(other_phases)

        kept_df = pd.concat(kept_list, ignore_index=True) if kept_list else pd.DataFrame()
        removed_df = pd.concat(removed_list, ignore_index=True) if removed_list else pd.DataFrame()

        return kept_df, removed_df, log


class PhaseTrendModel:
    """
    Models travel-time trend and adaptive sigma(x) bounds
    for a single seismic phase.
    """

    def __init__(self, config: PhaseTrendConfig):
        self.config = config
        self.predictor: Optional[Callable] = None
        self.sigma_function: Optional[Callable] = None
        self.poly = None
        self.fitted = False
        self.sigma_centers = None
        self.sigma_values = None
        self.x_min = None
        self.x_max = None


    @staticmethod
    def _remove_super_outliers(x, y, x_lower_percentile=0, x_upper_percentile=99,
                             y_lower_percentile=0, y_upper_percentile=99):
        """
        Remove extreme outliers based on percentiles.

        Parameters
        ----------
        x, y : array-like
        lower_percentile, upper_percentile : float

        Returns
        -------
        x_filtered, y_filtered : np.ndarray
        """
        x = np.array(x)
        y = np.array(y)

        x_min, x_max = np.percentile(x, [x_lower_percentile, x_upper_percentile])
        y_min, y_max = np.percentile(y, [y_lower_percentile, y_upper_percentile])

        mask = (x >= x_min) & (x <= x_max) & (y >= y_min) & (y <= y_max)

        return x[mask], y[mask]

    # -----------------------------
    # Fit model
    # -----------------------------
    def fit(self, x: np.ndarray, y: np.ndarray, scale=100,
             remove_outliers=False):
        if len(x) < self.config.min_points:
            return False

        if remove_outliers:
            x,y = self._remove_super_outliers(x, y)

        weights = 1 / (1 + x / scale)

        # Polynomial fit
        coeffs = np.polyfit(x, y, self.config.degree, w=weights)
        self.poly = np.poly1d(coeffs)
        self.predictor = lambda xx: self.poly(xx)

        residuals = y - self.predictor(x)
        self.sigma_function = self._compute_sigma_vs_distance(x, residuals)
        self.x_min = float(np.min(x))
        self.x_max = float(np.max(x))
        self.fitted = True
        return True

    
    # -----------------------------
    # Adaptive sigma(x)
    # -----------------------------
    def _compute_sigma_vs_distance(self, x, residuals):

        x_min, x_max = x.min(), x.max()

        # build distance edges
        edges_100 = np.arange(0, 1000 + 100, 100)
        edges_1000 = np.arange(1000, x_max + 1000, 1000)

        edges = np.unique(np.concatenate([
                                          edges_100, 
                                          edges_1000]))
        edges = edges[edges <= x_max]
        print(edges)

        centers = []
        sigmas = []

        for start, end in zip(edges[:-1], edges[1:]):

            mask = (x >= start) & (x < end)

            if np.sum(mask) > 5:
                r = residuals[mask]
                sigma_local = 1.4826 * np.median(
                    np.abs(r - np.median(r))
                )
            else:
                sigma_local = np.nan

            centers.append(0.5 * (start + end))
            sigmas.append(sigma_local)

        centers = np.array(centers)
        sigmas = np.array(sigmas)

        valid = ~np.isnan(sigmas)

        if np.sum(valid) < 2:
            global_sigma = 1.4826 * np.median(
                np.abs(residuals - np.median(residuals))
            )
            self.sigma_centers = np.array([x_min, x_max])
            self.sigma_values = np.array([global_sigma, global_sigma])
            return lambda xx: np.full_like(xx, global_sigma)

        # store interpolation data
        self.sigma_centers = centers[valid]
        self.sigma_values = sigmas[valid]

        return lambda xx: np.interp(xx, centers[valid], sigmas[valid])

    # -----------------------------
    # Bounds
    # -----------------------------
    def compute_bounds(self, x: np.ndarray, k: float):
        if not self.fitted:
            raise RuntimeError("Model must be fitted first.")

        y_pred = self.predictor(x)
        sigma_x = self.sigma_function(x)

        upper = y_pred + k * sigma_x
        lower = y_pred - k * sigma_x

        return y_pred, lower, upper
    

    def to_dict(self):
        if not self.fitted:
            print("Model must be fitted before export.")

        return {
            "degree": self.config.degree,
            "coefficients": self.poly.coefficients.tolist(),
            "phase": self.config.phase_order[0],
            "sigma_median": np.median(self.sigma_values),
            "sigma_max": np.max(self.sigma_values),
            "k": self.config.k_dict.get(self.config.phase_order[0], 5),
            "x_min": float(self.x_min),
            "x_max": float(self.x_max),
            "fitted": self.fitted,
        }

    def to_json(self, filepath):
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4)


# ============================================================
#  FILTERING (PANDAS LAYER)
# ============================================================

class LocalTrendFilter:
    """
    Applies PhaseTrendModel to DataFrames phase-by-phase.
    """

    def __init__(self, config: PhaseTrendConfig):
        self.config = config 
        self.models: Dict[str, PhaseTrendModel] = {}


    def to_dict(self):

        data = {}

        for phase, model in self.models.items():

            if not model.fitted:
                continue

            data[phase] = model.to_dict()

        return data
    

    def to_json(self, filepath):

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4)


    def filter_phase(
        self,
        df_phase: pd.DataFrame,
        phase: str,
        x_col="linear_hyp_distance",
        y_col="travel_time",
        log=None,
        debug=False
    ):

        if df_phase.empty:
            return df_phase.copy(), pd.DataFrame(), None

        #add zero bounds to avoid negative distances or times, which can cause issues with the model
        zero_row = {x_col: 0, y_col: 0, "phase": phase}
        for col in df_phase.columns:
            if col not in zero_row:
                zero_row[col] = np.nan
        df_phase = pd.concat([pd.DataFrame([zero_row]), df_phase], ignore_index=True)


        x = df_phase[x_col].values
        y = df_phase[y_col].values
        
        config = self.config.for_phase(phase)

        model = PhaseTrendModel(config)
        success = model.fit(x, y)


        if not success:
            return df_phase.copy(), pd.DataFrame(), None

        k = config.k_dict.get(phase, 2)
        y_pred, lower, upper = model.compute_bounds(x, k)

        lower = np.maximum(lower, 0)
        mask = (y >= lower) & (y <= upper)
        # mask = (y >= 0)

        kept = df_phase[mask].copy()
        removed = df_phase[~mask].copy()

        kept["lower_bound"] = lower[mask]
        kept["upper_bound"] = upper[mask]

        self.models[phase] = model

        print(kept[["linear_hyp_distance","travel_time"]].describe())

        # Logging
        if log is not None:
            step_removed = len(removed)
            log.add_step(f"local_trend_{phase}", step_removed,
                        thresholds={"k*sigma": k}, phase=phase)
            if debug:
                total_phase_picks = len(df_phase)
                print(f"[LocalTrend] Phase {phase}: removed {step_removed} "
                     f"(Phase cumulative: {log.cumulative_per_phase[phase]}/{total_phase_picks})")

        return kept, removed, model

    def apply(self, df, x_col="linear_hyp_distance", y_col="travel_time",
              log=None,
        debug=True):

        if log is None:
            log = QCLog()

        kept_list = []
        removed_list = []

        for phase in self.config.phase_order:
            df_phase = df[df["phase"] == phase]
            if df_phase.empty:
                continue

            df_phase = df_phase[df_phase[x_col]>=0]
            df_phase = df_phase[df_phase[y_col]>=0]

            kept, removed, _ = self.filter_phase(
                df_phase, phase, x_col, y_col, log=log, debug=debug
            )

            kept_list.append(kept)
            removed_list.append(removed)

        cleaned_df = pd.concat(kept_list, ignore_index=True)
        removed_df = pd.concat(removed_list, ignore_index=True)

        return cleaned_df, removed_df, log


def apply_phase_trend_qc(df, config: PhaseTrendConfig, 
                         apply_global=True, apply_local=True,
                         log=None, debug=True):

    cols = ["linear_hyp_distance", "travel_time", "phase"]

    # Rows where ANY of those columns has NaN
    df_nan = df[df[cols].isna().any(axis=1)].copy()

    # Rows where NONE of those columns has NaN
    df = df[df[cols].notna().all(axis=1)].copy()


    gt = GlobalTrendFilter()

    lt = LocalTrendFilter(config)

    if apply_global:
        df,rdf,log = gt.apply(df,log=log, debug=debug)
    if apply_local:
        df,r2df,log = lt.apply(df,log=log, debug=debug)

    df = pd.concat([df, df_nan], ignore_index=True)

    return df,gt,lt,log

def qc_run_to_dict(gt, lt, config, apply_global=True, apply_local=True):

    return {
        "qc_pipeline": {
            "apply_global": apply_global,
            "apply_local": apply_local
        },

        "config": {
            "phase_order": config.phase_order,
            "k_dict": config.k_dict,
            "min_points": config.min_points,
            "degree": config.degree,
            "fit_method": config.fit_method
        },

        "global_trends": gt.to_dict(),

        "local_models": lt.to_dict()
    }


def export_qc_run(filepath, gt, lt, config,
                  apply_global=True,
                  apply_local=True):

    data = qc_run_to_dict(
        gt,
        lt,
        config,
        apply_global=apply_global,
        apply_local=apply_local
    )

    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)


class PhasePlotter:
    """
    Visualizes fitted models and filtered picks.
    """

    def plot_phase(
        self,
        df_phase: pd.DataFrame,
        model: PhaseTrendModel,
        phase: str,
        k: float,
        x_col="linear_hyp_distance",
        y_col="travel_time",
        ax=None,
    ):

        if ax is None:
            fig, ax = plt.subplots(figsize=(4, 4))

        x = df_phase[x_col].values
        y = df_phase[y_col].values

        ax.scatter(x, y, s=5, color="black")

        if model is not None and model.fitted:

            x_fit = np.linspace(x.min(), x.max(), 200)
            y_fit, lower, upper = model.compute_bounds(x_fit, k)

            ax.plot(x_fit, y_fit, color="red", lw=2)
            ax.plot(x_fit, lower, "--", color="red")
            ax.plot(x_fit, upper, "--", color="red")

        ax.set_title(phase)
        ax.set_xlabel("Distance")
        ax.set_ylabel("Travel Time")

        return ax

    def plot_all(self, df, models, config: PhaseTrendConfig, figsize=(8, 10)):

        fig, axes = plt.subplots(2, 3, figsize=figsize)
        axes = axes.flatten()

        for i, phase in enumerate(config.phase_order):
            ax = axes[i]
            df_phase = df[df["phase"] == phase]

            model = models.get(phase)
            k = config.k_dict.get(phase, 5)

            self.plot_phase(
                df_phase,
                model,
                phase,
                k,
                ax=ax
            )

        plt.tight_layout()
        return fig, axes