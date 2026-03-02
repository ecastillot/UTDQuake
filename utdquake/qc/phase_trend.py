"""
Modular seismic phase trend modeling and filtering.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from dataclasses import dataclass, field
from typing import Dict, List
from .config import GLOBAL_TRENDS_DEFAULTS
from .log import QCLog

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class PhaseTrendConfig:
    phase_order: List[str] = field(default_factory=lambda: ["P", "Pn", "Pg", "S", "Sn", "Sg"])
    k_dict: Dict[str, float] = field(default_factory=lambda: {
        "P": 2, "Pn": 2, "Pg": 2, "S": 2, "Sn": 2, "Sg": 2
    })
    min_points: int = 20
    degree: int = 2
    fit_method: str = "polyfit"


class GlobalTrendFilter:
    """
    Apply a global (network-level) trend gate to seismic picks.

    Acts as a PRIOR filter before local adaptive modeling.
    """

    def __init__(self, global_trends=None):

        self.global_trends = global_trends or GLOBAL_TRENDS_DEFAULTS

        # Compile and save models
        self.models: Dict[str, dict] = {}

        for phase, info in self.global_trends.items():
            poly = np.poly1d(info["coefficients"])
            sigma = info.get("sigma_max", info.get("sigma_median"))
            k = info.get("k", 5)

            self.models[phase] = {
                "poly": poly,
                "sigma": sigma,
                "k": k,
                "x_min": info.get("x_min"),
                "x_max": info.get("x_max")
            }

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
            if df_phase.empty:
                continue

            x = df_phase[x_col].values
            y = df_phase[y_col].values

            y_pred, lower, upper = self.compute_bounds(x, phase)

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

    # -----------------------------
    # Fit model
    # -----------------------------
    def fit(self, x: np.ndarray, y: np.ndarray):
        if len(x) < self.config.min_points:
            return False

        # Polynomial fit
        coeffs = np.polyfit(x, y, self.config.degree)
        self.poly = np.poly1d(coeffs)
        self.predictor = lambda xx: self.poly(xx)

        residuals = y - self.predictor(x)
        self.sigma_function = self._compute_sigma_vs_distance(x, residuals)

        self.fitted = True
        return True

    
    # -----------------------------
    # Adaptive sigma(x)
    # -----------------------------
    def _compute_sigma_vs_distance(self, x, residuals, n_bins=50, overlap=0.7):

        x_min, x_max = x.min(), x.max()
        bin_width = (x_max - x_min) / n_bins
        step = bin_width * (1 - overlap)

        centers = []
        sigmas = []

        start = x_min
        while start < x_max:
            end = start + bin_width
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
            start += step

        centers = np.array(centers)
        sigmas = np.array(sigmas)

        valid = ~np.isnan(sigmas)

        if np.sum(valid) < 2:
            global_sigma = 1.4826 * np.median(
                np.abs(residuals - np.median(residuals))
            )
            return lambda xx: np.full_like(xx, global_sigma)

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

        x = df_phase[x_col].values
        y = df_phase[y_col].values

        model = PhaseTrendModel(self.config)
        success = model.fit(x, y)

        if not success:
            return df_phase.copy(), pd.DataFrame(), None

        k = self.config.k_dict.get(phase, 2)
        y_pred, lower, upper = model.compute_bounds(x, k)

        mask = (y >= lower) & (y <= upper)

        kept = df_phase[mask].copy()
        removed = df_phase[~mask].copy()

        kept["lower_bound"] = lower[mask]
        kept["upper_bound"] = upper[mask]

        self.models[phase] = model

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

            kept, removed, _ = self.filter_phase(
                df_phase, phase, x_col, y_col, log=log, debug=debug
            )

            kept_list.append(kept)
            removed_list.append(removed)

        cleaned_df = pd.concat(kept_list, ignore_index=True)
        removed_df = pd.concat(removed_list, ignore_index=True)

        return cleaned_df, removed_df, log


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