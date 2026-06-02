"""
Travel-time quality control and modeling utilities.

This module provides tools to:
- Build travel-time statistical models using percentiles
- Clean seismic phase data
- Compute QC metrics (residuals, z-scores, bounds)
- Handle multi-phase workflows

The models are based on distance-dependent statistics and
polynomial interpolation.

Example
-------
>>> model = PhaseTravelTimeModel(df_model)
>>> preds = model.predict(np.array([1000, 2000]))
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.interpolate import interp1d


from typing import Dict, List, Optional, Tuple, Union
from .config import GLOBAL_TRENDS_DEFAULTS_DEG2
from ..writers.schema import sanitize_dataframe

class PhaseTravelTimeModel:
    """
    Travel-time model using polynomial interpolation of percentiles.

    Parameters
    ----------
    model_df : pandas.DataFrame
        DataFrame containing at least:
        - ``distance_center`` (float)
        - ``sigma`` (float)
        - percentile columns (e.g., ``tt_p50``, ``tt_p1``, etc.)

    Raises
    ------
    ValueError
        If the input DataFrame is empty or invalid.

    Notes
    -----
    - Polynomial interpolation is used for smooth curves.
    - Automatically handles small datasets by reducing polynomial degree.
    """
    def __init__(self, model_df: pd.DataFrame) -> None:
        if model_df.empty:
            raise ValueError("model_df is empty.")

        # Sort by distance to ensure monotonic input
        self.model_df: pd.DataFrame = (
            model_df.sort_values("distance_center").reset_index(drop=True)
        )

        # Build interpolation functions
        self._build_interpolators()

    def _build_interpolators(self, poly_deg: int = 2) -> None:
        """
        Build polynomial interpolators for sigma and percentile curves.

        Parameters
        ----------
        poly_deg : int, optional
            Maximum polynomial degree (default is 2).

        Raises
        ------
        ValueError
            If no valid rows are available.
        """

        # -------------------------
        # Prepare data
        # -------------------------
        # Only keep rows with valid sigma and at least one percentile
        percentile_cols = [col for col in self.model_df.columns if col.startswith("travel_time_p")]
        required_cols = ["travel_time_sigma"] + percentile_cols
        df_valid = self.model_df.dropna(subset=required_cols)
        df_valid = df_valid.sort_values("distance_center").reset_index(drop=True)

        if len(df_valid) == 0:
            raise ValueError("No valid rows available to build interpolators.")

        # Remove duplicate distances (needed for polyfit)
        df_valid = df_valid.drop_duplicates(subset="distance_center")

        x = df_valid["distance_center"].values


        # -------------------------
        # Sigma (robust)
        # -------------------------
        y_sigma = df_valid["travel_time_sigma"].values

        # Ensure enough points for requested degree
        deg_sigma = min(poly_deg, len(x) - 1)
        if deg_sigma <= 0:
            # fallback: just constant sigma
            self.std_func = lambda d: np.full_like(d, y_sigma[0] if len(y_sigma) > 0 else 0.0, dtype=float)
        else:
            # self.sigma_coeff = np.polyfit(x, y_sigma, deg_sigma)
            # self.std_func = np.poly1d(self.sigma_coeff)
            self.std_func = interp1d(
                    x,
                    y_sigma,
                    kind="linear",           
                    bounds_error=False,
                    fill_value="extrapolate"
                )

        # -------------------------
        # Percentiles
        # -------------------------
        self.p_funcs = {}
        for col in percentile_cols:
            y = df_valid[col].values
            deg_col = min(poly_deg, len(x) - 1)
            if deg_col <= 0:
                # fallback: constant curve
                self.p_funcs[col] = lambda d, val=y[0]: np.full_like(d, val, dtype=float)
            else:
                # coeff = np.polyfit(x, y, deg_col)
                # self.p_funcs[col] = np.poly1d(coeff)
                self.p_funcs[col] = interp1d(
                                        x,
                                        y,
                                        kind="linear",
                                        bounds_error=False,
                                        fill_value="extrapolate"
                                    )

    def predict(self, distance: np.ndarray) -> pd.DataFrame:
        """
        Predict sigma and percentile curves at given distances.

        Parameters
        ----------
        distance : numpy.ndarray
            Array of distances.

        Returns
        -------
        pandas.DataFrame
            DataFrame with predicted sigma and percentiles.
        """
        distance = np.asarray(distance)

        result = {
            "distance": distance,
            "travel_time_sigma": self.std_func(distance)
        }

        for name, func in self.p_funcs.items():
            result[name] = func(distance)

        return pd.DataFrame(result)

    def compute_residuals(
        self,
        distance: np.ndarray,
        travel_time: np.ndarray,
        ) -> pd.DataFrame:
        """
        Compute residuals relative to percentile curves.

        Parameters
        ----------
        distance : numpy.ndarray
            Distances.
        travel_time : numpy.ndarray
            Observed travel times.

        Returns
        -------
        pandas.DataFrame
            Residuals for each percentile curve.
        """
        distance = np.asarray(distance)
        travel_time = np.asarray(travel_time)

        preds = self.predict(distance)

        residuals = {}

        for col in preds.columns:
            if col.startswith("travel_time_p"):
                residuals[f"QC_tt_res_{col}"] = travel_time - preds[col]

        return pd.DataFrame(residuals)

    def compute_bounds(
        self,
        distance: np.ndarray,
        p_low: int = 1,
        p_high: int = 99,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute percentile-based bounds.

        Parameters
        ----------
        distance : numpy.ndarray
            Distances.
        p_low : int, optional
            Lower percentile (default is 1).
        p_high : int, optional
            Upper percentile (default is 99).

        Returns
        -------
        tuple of numpy.ndarray
            Lower and upper bounds.
        """
        distance = np.asarray(distance)

        lower = self.p_funcs[f"travel_time_p{p_low}"](distance)
        upper = self.p_funcs[f"travel_time_p{p_high}"](distance)

        return lower, upper

    def compute_sigma_bounds(
        self,
        distance: np.ndarray,
        k: float = 3.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute bounds using median ± k * sigma.

        Parameters
        ----------
        distance : numpy.ndarray
            Distances.
        k : float, optional
            Number of standard deviations (default is 3).

        Returns
        -------
        tuple of numpy.ndarray
            Lower and upper bounds.
        """
        distance = np.asarray(distance)

        median = self.p_funcs["travel_time_p50"](distance)
        #check nans in median
        sigma = self.std_func(distance)
        sigma = np.abs(sigma)                  # ensure positive


        lower = median - k * sigma
        upper = median + k * sigma

        return lower, upper

    def classify(
        self,
        distance: np.ndarray,
        travel_time: np.ndarray,
        method: str = "percentile",
        p_low: int = 1,
        p_high: int = 99,
        k: float = 3.0,
        return_bounds: bool = False,
    ):
        """
        Classify observations as inside/outside model bounds.

        Parameters
        ----------
        distance : numpy.ndarray
            Distances.
        travel_time : numpy.ndarray
            Observed travel times.
        method : {'percentile', 'sigma'}, optional
            Method to compute bounds.
        p_low : int, optional
            Lower percentile.
        p_high : int, optional
            Upper percentile.
        k : float, optional
            Sigma multiplier.
        return_bounds : bool, optional
            If True, also return bounds.

        Returns
        -------
        numpy.ndarray or tuple
            Boolean mask, optionally with bounds.
        """
        distance = np.asarray(distance)
        travel_time = np.asarray(travel_time)

        if method == "percentile":
            lower, upper = self.compute_bounds(distance, p_low, p_high)

        elif method == "sigma":
            lower, upper = self.compute_sigma_bounds(distance, k=k)

        else:
            raise ValueError("method must be 'percentile' or 'sigma'")

        inside = (travel_time >= lower) & (travel_time <= upper)

        if return_bounds:
            return inside, lower, upper

        return inside

    def save(self, filepath: str) -> None:
        """
        Save model to disk.

        Parameters
        ----------
        filepath : str
            Output file path (.csv or .parquet).
        """
        if filepath.endswith(".csv"):
            self.model_df.to_csv(filepath, index=False)
        elif filepath.endswith(".parquet"):
            self.model_df.to_parquet(filepath, index=False)
        else:
            raise ValueError("Unsupported format.")

    @classmethod
    def load(cls, filepath: str):
        """
        Load model from disk.

        Parameters
        ----------
        filepath : str
            Input file path.

        Returns
        -------
        PhaseTravelTimeModel
            Loaded model instance.
        """
        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
        elif filepath.endswith(".parquet"):
            df = pd.read_parquet(filepath)
        else:
            raise ValueError("Unsupported format.")

        return cls(df)

class PhaseTravelTime:
    """
    Handle travel-time data processing and model construction for a given phase.

    Parameters
    ----------
    df : pandas.DataFrame
        Input dataset containing phase, distance, and travel time.
    distance_col : str
        Column name for distance.
    tt_col : str
        Column name for travel time.
    phase : str
        Phase to filter (e.g., "P", "S").

    Notes
    -----
    - Original data is preserved.
    - Cleaning only affects internal arrays used for modeling.
    """


    def __init__(
            self,
            df: pd.DataFrame,
            distance_col: str,
            tt_col: str,
            phase: str,
        ) -> None:
        self.df_full = df.copy()  # Keep all original rows
        self.distance_col = distance_col
        self.tt_col = tt_col
        self.phase = phase

        # Only valid rows (non-NaN in distance or travel_time) for QC processing
        self.df_valid = self.df_full[
            (self.df_full["phase"] == phase) &
            (~self.df_full[distance_col].isna()) &
            (~self.df_full[tt_col].isna())
        ].copy()

        self.d = self.df_valid[distance_col].values
        self.t = self.df_valid[tt_col].values

        self.d_clean = self.d.copy()
        self.t_clean = self.t.copy()

        self.bins = None
        self.global_trends = GLOBAL_TRENDS_DEFAULTS_DEG2
        self.global_model = None
        self.global_mask = None

    # ---------------------------------------------------------------------
    # Cleaning
    # ---------------------------------------------------------------------
    @staticmethod
    def remove_xy_outliers_mahalanobis(
        x: np.ndarray,
        y: np.ndarray,
        threshold: float = 3.0,
    ) -> np.ndarray:
        """
        Detect outliers using Mahalanobis distance.

        Parameters
        ----------
        x, y : numpy.ndarray
            Input data.
        threshold : float, optional
            Distance threshold.

        Returns
        -------
        numpy.ndarray
            Boolean mask of inliers.
        """
        xy = np.vstack([x, y]).T
        cov = np.cov(xy, rowvar=False)
        mean = np.mean(xy, axis=0)

        diff = xy - mean
        inv_cov = np.linalg.pinv(cov)

        md = np.sqrt(np.sum(diff @ inv_cov * diff, axis=1))
        return md <= threshold

    def clean_data(
        self,
        use_global: bool = True,
        use_mahalanobis: bool = False,
        mahalanobis_threshold: float = 3.0,
    ) -> None:
        """
        Build a mask of clean data for model construction.

        Parameters
        ----------
        use_global : bool, optional
            Apply global trend filtering.
        use_mahalanobis : bool, optional
            Apply Mahalanobis outlier detection.
        mahalanobis_threshold : float, optional
            Threshold for Mahalanobis filtering.
        """

        # Start with all True
        mask = np.ones_like(self.d, dtype=bool)

        if use_global:
            mask_global = self.compute_global_mask()
            mask &= mask_global

        if use_mahalanobis:
            mask_maha = self.remove_xy_outliers_mahalanobis(
                self.d, self.t, mahalanobis_threshold
            )
            mask &= mask_maha

        # Store mask (important for debugging / future weighting)
        self.clean_mask = mask

        self.d_clean = self.d[mask]
        self.t_clean = self.t[mask]

    def compute_global_mask(
        self,
        k_override: Optional[float] = None,
    ) -> np.ndarray:
        """
        Compute mask of points consistent with global trend.

        Parameters
        ----------
        k_override : float, optional
            Override sigma multiplier.

        Returns
        -------
        numpy.ndarray
            Boolean mask.
        """

        if self.phase not in self.global_trends:
            self.global_mask = np.ones_like(self.d, dtype=bool)
            return self.global_mask

        info = self.global_trends[self.phase]

        poly = np.poly1d(info["coefficients"])

        # Prefer median (more stable than sigma_max)
        sigma = info.get("sigma_median")
        k = k_override if k_override is not None else info.get("k", 5)

        y_pred = poly(self.d)

        lower = np.maximum(0, y_pred - k * sigma)
        upper = y_pred + k * sigma

        mask = (self.t >= lower) & (self.t <= upper)

        self.global_mask = mask
        return mask

    # ---------------------------------------------------------------------
    # Binning
    # ---------------------------------------------------------------------
    def build_bins(
        self,
        n_bins: int = 100,
        dmin: float = 0.0,
        dmax: float = 30e3,
        alpha: float = 3.0,
    ) -> np.ndarray:
        """
        Build non-linear distance bins using power-law stretching.

        Parameters
        ----------
        n_bins : int
            Number of bins.
        dmin, dmax : float
            Distance range.
        alpha : float
            Stretching parameter.

        Returns
        -------
        numpy.ndarray
            Bin edges.
        """

        u = np.linspace(0, 1, n_bins)


        # Smooth stretching
        bins = dmin + (dmax - dmin) * (u ** alpha)

        self.bins = bins
        return self.bins

    # ---------------------------------------------------------------------
    # Model building
    # ---------------------------------------------------------------------
    def build_model(
        self,
        min_points_per_bin: int = 5,
        percentiles: Tuple[int, ...] = (1, 25, 50, 75, 99),
    ):
        """
        Build PhaseTravelTimeModel using binned statistics.

        Parameters
        ----------
        min_points_per_bin : int
            Minimum samples required per bin.
        percentiles : tuple of int
            Percentiles to compute.

        Returns
        -------
        PhaseTravelTimeModel
            Constructed model.
        """

        if self.bins is None:
            raise ValueError("Run build_bins first.")

        centers = self.bins[:-1] + np.diff(self.bins) / 2

        rows = []

        for i in range(len(self.bins) - 1):
            mask = (self.d_clean >= self.bins[i]) & (self.d_clean < self.bins[i + 1])

            if np.sum(mask) >= min_points_per_bin:
                t_bin = self.t_clean[mask]

                row = {
                    "distance_min": self.bins[i],
                    "distance_max": self.bins[i + 1],
                    "distance_center": centers[i],
                    "count": np.sum(mask),
                }

                # direct travel-time percentiles
                for p in percentiles:
                    row[f"travel_time_p{p}"] = np.percentile(t_bin, p)

                # robust sigma around median
                median = row["travel_time_p50"]
                row["travel_time_sigma"] = 1.4826 * np.median(np.abs(t_bin - median))

            else:
                row = {
                    "distance_min": self.bins[i],
                    "distance_max": self.bins[i + 1],
                    "distance_center": centers[i],
                    "count": 0,
                }
                for p in percentiles:
                    row[f"travel_time_p{p}"] = np.nan
                row["travel_time_sigma"] = np.nan

            rows.append(row)

        model_df = pd.DataFrame(rows)


        return PhaseTravelTimeModel(model_df)

    def attach_zscore(self, model) -> pd.DataFrame:
        """
        Attach z-score based on model median and sigma.

        Returns
        -------
        pandas.DataFrame
        """
        df = self.df_full.copy()
        df = df.sort_values(self.distance_col).reset_index(drop=True)

        valid_mask = (
            (~df[self.distance_col].isna()) &
            (~df[self.tt_col].isna()) &
            (df["phase"] == self.phase)
        )

        x = df.loc[valid_mask, self.distance_col].values
        y = df.loc[valid_mask, self.tt_col].values

        # Use model prediction (clean + consistent)
        preds = model.predict(x)
        

        mu = preds["travel_time_p50"].values
        sigma = preds["travel_time_sigma"].values

        # Avoid division by zero / negative sigma
        sigma = np.where(np.abs(sigma) < 1e-12, np.nan, np.abs(sigma))

        z = (y - mu) / sigma

        # print(df[["phase","linear_hyp_distance","travel_time","travel_time_zscore"]].head())
        # print(x[:5],y[:5], mu[:5], sigma[:5], z[:5])

        df.loc[valid_mask, "travel_time_zscore"] = z

        return df


    def attach_qc_features(
        self,
        model,
        classify: Optional[
            Union[Tuple[int, int], List[Tuple[int, int]]]
        ] = None,
    ) -> pd.DataFrame:
        """
        Attach residuals and classification flags.

        Parameters
        ----------
        model : PhaseTravelTimeModel
            Model instance.
        classify : tuple or list of tuples, optional
            Percentile ranges.

        Returns
        -------
        pandas.DataFrame
        """
        df = self.df_full.copy()

        # Only compute residuals for valid rows
        valid_mask = (~df[self.distance_col].isna()) & (~df[self.tt_col].isna()) & (df["phase"] == self.phase)

        x = df.loc[valid_mask, self.distance_col].values
        t_obs = df.loc[valid_mask, self.tt_col].values

        # residuals relative to all percentile curves
        residuals = model.compute_residuals(x, t_obs)
        df.loc[valid_mask, residuals.columns] = residuals.values

        if classify is not None:
            if isinstance(classify, tuple):
                classify = [classify]

            for p_low, p_high in classify:
                df.loc[valid_mask, f"inside_p{p_low}_p{p_high}"] = model.classify(x, t_obs, p_low=p_low, p_high=p_high)

        return df

class TravelTimeModel:
    """
    Wrapper for multiple PhaseTravelTimeModel objects, one per seismic phase.

    This class manages a collection of :class:`PhaseTravelTimeModel` instances,
    allowing unified access to travel-time models for different phases
    (e.g., P, S).

    Parameters
    ----------
    model_df : pandas.DataFrame
        DataFrame containing model data for all phases. Must include
        a ``phase`` column to separate models.

    Raises
    ------
    ValueError
        If the DataFrame is empty or missing the ``phase`` column.
    """

    def __init__(self, model_df: pd.DataFrame):
        if model_df.empty:
            raise ValueError("model_df is empty.")

        if "phase" not in model_df.columns:
            raise ValueError("model_df must contain 'phase' column for multi-phase model.")

        self.models = {}
        self.phases = model_df["phase"].unique()

        for phase in self.phases:
            df_phase = model_df[model_df["phase"] == phase].copy()
            try:
                self.models[phase] = PhaseTravelTimeModel(df_phase)
            except:
                print(f"Warning: Failed to build model for phase {phase}. Skipping.")

    def get_model(self, phase:str) -> PhaseTravelTimeModel:
        """
        Retrieve the model corresponding to a given phase.

        Parameters
        ----------
        phase : str
            Phase name (e.g., "P", "S").

        Returns
        -------
        PhaseTravelTimeModel
            Corresponding model.

        Raises
        ------
        ValueError
            If the phase is not available.
        """
        if phase not in self.models:
            raise ValueError(f"No model for phase {phase}")
        return self.models[phase]

    def predict(self, phase:str, distance: np.ndarray) -> pd.DataFrame:
        """
        Predict travel-time statistics for a given phase.

        Parameters
        ----------
        phase : str
            Phase name.
        distance : int, float or numpy.ndarray
            Distances at which to predict.

        Returns
        -------
        pandas.DataFrame
            Predicted sigma and percentile curves.
        """
        if isinstance(distance, (int, float)):
            distance = np.array([distance])
        return self.get_model(phase).predict(distance)

    # ---------------------------------------------------------------------
    # Residuals
    # ---------------------------------------------------------------------
    def compute_residuals(self, phase:str, distance:np.array, travel_time:np.array) -> pd.DataFrame:
        """
        Compute residuals relative to percentile curves.

        Parameters
        ----------
        phase : str
            Phase name.
        distance : numpy.ndarray
            Distances.
        travel_time : numpy.ndarray
            Observed travel times.

        Returns
        -------
        pandas.DataFrame
            Residuals per percentile.
        """
        return self.get_model(phase).compute_residuals(distance, travel_time)

    def compute_bounds(self, phase, distance, p_low=1, p_high=99):
        """
        Compute percentile-based bounds.

        Parameters
        ----------
        phase : str
            Phase name.
        distance : numpy.ndarray
            Distances.
        p_low : int, optional
            Lower percentile.
        p_high : int, optional
            Upper percentile.

        Returns
        -------
        tuple of numpy.ndarray
            Lower and upper bounds.
        """
        return self.get_model(phase).compute_bounds(distance, p_low, p_high)

    def compute_sigma_bounds(self, phase:str, distance:np.array, k:float=3.0):
        """
        Compute sigma-based bounds (median ± k*sigma).

        Parameters
        ----------
        phase : str
            Phase name.
        distance : numpy.ndarray
            Distances.
        k : float, optional
            Sigma multiplier.

        Returns
        -------
        tuple of numpy.ndarray
            Lower and upper bounds.
        """
        return self.get_model(phase).compute_sigma_bounds(distance, k=k)

    def classify(
        self,
        phase:str,
        distance:np.array,
        travel_time:np.array,
        method:str="percentile",
        p_low:int=1,
        p_high:int=99,
        k:float=3.0,
    ):
        """
        Classify observations as inside or outside model bounds.

        Parameters
        ----------
        phase : str
            Phase name.
        distance : numpy.ndarray
            Distances.
        travel_time : numpy.ndarray
            Observed travel times.
        method : {'percentile', 'sigma'}, optional
            Method used for bounds.
        p_low, p_high : int, optional
            Percentile bounds.
        k : float, optional
            Sigma multiplier.

        Returns
        -------
        numpy.ndarray
            Boolean mask indicating whether each observation is inside bounds.
        """
        return self.get_model(phase).classify(
            distance,
            travel_time,
            method=method,
            p_low=p_low,
            p_high=p_high,
            k=k
        )

    def save(self, filepath:str) -> None:
        """
        Save all phase models into a single file.

        Each phase model is combined into one DataFrame with a ``phase`` column.

        Parameters
        ----------
        filepath : str
            Output file path (.csv or .parquet).
        """
        dfs = []
        for phase, model in self.models.items():
            df = model.model_df.copy()
            df["phase"] = phase
            dfs.append(df)
        if dfs:
            df_all = pd.concat(dfs, ignore_index=True)
            if filepath.endswith(".parquet"):
                df_all.to_parquet(filepath, index=False)
            elif filepath.endswith(".csv"):
                df_all.to_csv(filepath, index=False)
            else:
                raise ValueError("Unsupported format. Use .parquet or .csv")

    @classmethod
    def load(cls, filepath:str):
        """
        Load a multi-phase model from disk.

        Parameters
        ----------
        filepath : str
            Input file path (.csv or .parquet).

        Returns
        -------
        TravelTimeModel
            Loaded multi-phase model.

        Raises
        ------
        ValueError
            If file format is unsupported or missing ``phase`` column.
        """
        filepath = Path(filepath)  # ensure it's a Path object

        if filepath.suffix == ".csv":
            df = pd.read_csv(filepath)
        elif filepath.suffix == ".parquet":
            df = pd.read_parquet(filepath)
        else:
            raise ValueError("Unsupported format. Use .parquet or .csv")

        if "phase" not in df.columns:
            raise ValueError("Loaded model must contain 'phase' column.")

        return cls(df)

class TravelTime:
    """
    Multi-phase travel-time QC manager.

    This class wraps multiple :class:`PhaseTravelTime` objects (one per phase)
    and provides a unified interface for:
        - Cleaning
        - Model building
        - QC feature computation

    Parameters
    ----------
    df : pandas.DataFrame
        Input dataset containing at least:
        - ``phase``
        - distance column
        - travel-time column
    distance_col : str, optional
        Name of the distance column.
    tt_col : str, optional
        Name of the travel-time column.
    phases : list of str, optional
        List of phases to process. Defaults to common seismic phases.

    Notes
    -----
    - Each phase is processed independently.
    - Results can be combined into a single QC DataFrame.
    """
    DEFAULT_PHASES = ["P", "S", "Pn", "Sn", "Pg", "Sg"]

    def __init__(self, df: pd.DataFrame, distance_col="linear_hyp_distance", tt_col="travel_time",
                 phases=None):
        self.df = df.copy()
        self.distance_col = distance_col
        self.tt_col = tt_col
        self.phases = phases or self.DEFAULT_PHASES

        # Internal PhaseTravelTime objects keyed by phase
        self.qc_objects = {}
        self.models = {}
        self.df_qc_all = pd.DataFrame()

        # Initialize QC objects for each phase
        for phase in self.phases:
            df_phase = df[df["phase"] == phase].copy()
            if not df_phase.empty:
                self.qc_objects[phase] = PhaseTravelTime(df_phase, distance_col, tt_col, phase)

    def clean_data(
        self,
        use_global: bool = True,
        use_mahalanobis: bool = False,
        mahalanobis_threshold: float = 3.0,
    ) -> None:
        """
        Apply cleaning to all phases.

        Parameters
        ----------
        use_global : bool
            Apply global trend filtering.
        use_mahalanobis : bool
            Apply Mahalanobis outlier detection.
        mahalanobis_threshold : float
            Threshold for Mahalanobis distance.
        """

        for qc in self.qc_objects.values():
            qc.clean_data(
                use_global=use_global,
                use_mahalanobis=use_mahalanobis,
                mahalanobis_threshold=mahalanobis_threshold
            )

    def build_bins(
        self,
        n_bins: int = 100,
        dmin: float = 0.0,
        dmax: float = 30e3,
        alpha: float = 3.0,
    ) -> None:
        """
        Build distance bins for all phases.

        Parameters
        ----------
        n_bins : int
            Number of bins.
        dmin, dmax : float
            Distance range.
        alpha : float
            Power-law stretching parameter.
        """
        for qc in self.qc_objects.values():
            qc.build_bins(n_bins=n_bins, dmin=dmin, dmax=dmax,
                          alpha=alpha)

    def build_models(
        self,
        min_points_per_bin: int = 5,
        percentiles: Tuple[int, ...] = (1, 25, 50, 75, 99),
    ) -> Dict[str, "PhaseTravelTimeModel"]:
        """
        Build PhaseTravelTimeModel for each phase.

        Parameters
        ----------
        min_points_per_bin : int
            Minimum samples per bin.
        percentiles : tuple of int
            Percentiles to compute.

        Returns
        -------
        dict
            Dictionary of models keyed by phase.
        """
        for phase, qc in self.qc_objects.items():
            try:
                self.models[phase] = qc.build_model(min_points_per_bin=min_points_per_bin,
                                                percentiles=percentiles)
            except Exception as e:
                print(f"Warning: Failed to build model for phase {phase}. Error: {e}")
        return self.models
        

    def attach_zscore(self) -> pd.DataFrame:
        """
        Compute and attach travel-time z-scores for all phases.

        Returns
        -------
        pandas.DataFrame
            Concatenated DataFrame with ``tt_zscore`` column.
        """
        dfs = []
        for phase, qc in self.qc_objects.items():
            model = self.models.get(phase)
            if model is None:
                continue
            df_z = qc.attach_zscore(model)
            dfs.append(df_z)
        
        if dfs:
            self.df_qc_all = pd.concat(dfs, ignore_index=True)
        return self.df_qc_all

    def attach_qc_features(
        self,
        classify: Optional[
            Union[Tuple[int, int], List[Tuple[int, int]]]
        ] = None) -> pd.DataFrame:
        """
        Attach residuals and QC classification flags.

        Parameters
        ----------
        classify : tuple or list of tuples, optional
            Percentile bounds for classification.

        Returns
        -------
        pandas.DataFrame
            QC-enriched DataFrame.
        """
        dfs_qc = []
        for phase, qc in self.qc_objects.items():
            model = self.models.get(phase)
            if model is None:
                continue
            df_qc = qc.attach_qc_features(model, classify=classify)
            df_qc["phase"] = phase
            dfs_qc.append(df_qc)
        if dfs_qc:
            self.df_qc_all = pd.concat(dfs_qc, ignore_index=True)
        return self.df_qc_all

    def save_models_combined(self, filepath: str) -> None:
        """
        Save all phase models into a single file.

        Parameters
        ----------
        filepath : str
            Output path (.csv or .parquet).
        """
        dfs = []
        for phase, model in self.models.items():
            df = model.model_df.copy()
            df["phase"] = phase
            dfs.append(df)
        if dfs:
            df_all = pd.concat(dfs, ignore_index=True)

            float_cols = [col for col in df_all.columns if col not in ["phase"]]
            str_cols = ["phase"]
            df_all = sanitize_dataframe(df_all, 
                            float_cols=float_cols, 
                            string_cols=str_cols)
            if str(filepath).endswith(".parquet"):
                df_all.to_parquet(filepath, index=False)
            elif str(filepath).endswith(".csv"):
                df_all.to_csv(filepath, index=False)
            else:
                raise ValueError("Unsupported format. Use .parquet or .csv")
            print(f"Saved combined model to {filepath}")
        else:
            print("No models to save.")

    def save_qc_dataframe(self, filepath: str) -> None:
        """
        Save QC DataFrame to disk.

        Parameters
        ----------
        filepath : str
            Output path.
        """
        if filepath.endswith(".parquet"):
            self.df_qc_all.to_parquet(filepath, index=False)
        elif filepath.endswith(".csv"):
            self.df_qc_all.to_csv(filepath, index=False)
        else:
            raise ValueError("Unsupported format. Use .parquet or .csv")

    def compute_residuals(
        self,
        phase: str,
        distance: Optional[np.ndarray] = None,
        travel_time: Optional[np.ndarray] = None,
    ) -> pd.DataFrame:
        """
        Compute residuals relative to all percentile curves for a specific phase.

        Parameters
        ----------
        phase : str
            Name of the seismic phase.
        distance : np.ndarray, optional
            Distances to compute residuals for. Defaults to cleaned distances for the phase.
        travel_time : np.ndarray, optional
            Travel times corresponding to distances. Defaults to cleaned travel times for the phase.

        Returns
        -------
        pd.DataFrame
            Residuals for each requested distance and travel time, with columns
            corresponding to the percentile residuals.
        """
        model = self.models.get(phase)
        if model is None:
            raise ValueError(f"No model for phase {phase}")
        qc = self.qc_objects[phase]
        distance = distance or qc.d_clean
        travel_time = travel_time or qc.t_clean
        return model.compute_residuals(distance, travel_time)

    def compute_bounds(
        self,
        phase: str,
        distance: Optional[np.ndarray] = None,
        p_low: int = 1,
        p_high: int = 99,
    ) -> pd.DataFrame:
        """
        Compute percentile bounds for a specific phase.

        Parameters
        ----------
        phase : str
            Name of the seismic phase.
        distance : np.ndarray, optional
            Distances at which to compute bounds. Defaults to cleaned distances.
        p_low : int
            Lower percentile (inclusive).
        p_high : int
            Upper percentile (inclusive).

        Returns
        -------
        pd.DataFrame
            DataFrame with lower and upper bounds for each requested distance.
        """
        model = self.models.get(phase)
        if model is None:
            raise ValueError(f"No model for phase {phase}")
        qc = self.qc_objects[phase]
        distance = distance or qc.d_clean
        return model.compute_bounds(distance, p_low, p_high)

    def compute_sigma_bounds(
        self,
        phase: str,
        distance: Optional[np.ndarray] = None,
        k: float = 3.0,
    ) -> pd.DataFrame:
        """
        Compute median ± k*sigma bounds for a specific phase.

        Parameters
        ----------
        phase : str
            Name of the seismic phase.
        distance : np.ndarray, optional
            Distances at which to compute sigma bounds. Defaults to cleaned distances.
        k : float
            Number of robust sigmas to define bounds.

        Returns
        -------
        pd.DataFrame
            DataFrame with lower and upper bounds (median ± k*sigma) for each distance.
        """
        model = self.models.get(phase)
        if model is None:
            raise ValueError(f"No model for phase {phase}")
        qc = self.qc_objects[phase]
        distance = distance or qc.d_clean
        return model.compute_sigma_bounds(distance, k=k)

    def classify(
        self,
        phase: str,
        distance: Optional[np.ndarray] = None,
        travel_time: Optional[np.ndarray] = None,
        p_low: int = 1,
        p_high: int = 99,
    ) -> np.ndarray:
        """
        Classify picks as inside or outside bounds for a specific phase.

        Parameters
        ----------
        phase : str
            Name of the seismic phase.
        distance : np.ndarray, optional
            Distances corresponding to picks. Defaults to cleaned distances.
        travel_time : np.ndarray, optional
            Travel times corresponding to picks. Defaults to cleaned travel times.
        p_low : int
            Lower percentile for classification.
        p_high : int
            Upper percentile for classification.

        Returns
        -------
        np.ndarray
            Boolean array: True if pick is within the bounds, False otherwise.
        """
        model = self.models.get(phase)
        if model is None:
            raise ValueError(f"No model for phase {phase}")
        qc = self.qc_objects[phase]
        distance = distance or qc.d_clean
        travel_time = travel_time or qc.t_clean
        return model.classify(distance, travel_time, p_low=p_low, p_high=p_high)
