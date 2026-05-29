# qc_travel_time.py
from .config import GLOBAL_TRENDS_DEFAULTS_DEG2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.interpolate import interp1d




class TravelTimeModel:
    """
    Statistical travel-time model based on distance-dependent percentiles.
    """

    def __init__(self, model_df: pd.DataFrame):
        if model_df.empty:
            raise ValueError("model_df is empty.")

        self.model_df = model_df.sort_values("distance_center").reset_index(drop=True)

        self._build_interpolators()

    def _build_interpolators(self, poly_deg=2):
        """
        Build polynomial-based interpolators for sigma and travel-time percentiles.
        Safe against NaNs, zeros, duplicates, and too few points.
        """

        # -------------------------
        # Prepare data
        # -------------------------
        # Only keep rows with valid sigma and at least one percentile
        percentile_cols = [col for col in self.model_df.columns if col.startswith("tt_p")]
        required_cols = ["sigma"] + percentile_cols
        df_valid = self.model_df.dropna(subset=required_cols)

        if len(df_valid) == 0:
            raise ValueError("No valid rows available to build interpolators.")

        # Remove duplicate distances (needed for polyfit)
        df_valid = df_valid.drop_duplicates(subset="distance_center")

        x = df_valid["distance_center"].values


        # -------------------------
        # Sigma (robust)
        # -------------------------
        y_sigma = df_valid["sigma"].values

        # Ensure enough points for requested degree
        deg_sigma = min(poly_deg, len(x) - 1)
        if deg_sigma <= 0:
            # fallback: just constant sigma
            self.std_func = lambda d: np.full_like(d, y_sigma[0] if len(y_sigma) > 0 else 0.0, dtype=float)
        else:
            self.sigma_coeff = np.polyfit(x, y_sigma, deg_sigma)
            self.std_func = np.poly1d(self.sigma_coeff)

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
                coeff = np.polyfit(x, y, deg_col)
                self.p_funcs[col] = np.poly1d(coeff)

    # ---------------------------------------------------------------------
    # Prediction
    # ---------------------------------------------------------------------
    def predict(self, distance: np.ndarray) -> pd.DataFrame:
        """
        Interpolate all model curves at given distances.
        """
        distance = np.asarray(distance)

        result = {
            "distance": distance,
            "sigma": self.std_func(distance)
        }

        for name, func in self.p_funcs.items():
            result[name] = func(distance)

        return pd.DataFrame(result)

    # ---------------------------------------------------------------------
    # Residuals
    # ---------------------------------------------------------------------
    def compute_residuals(self, distance, travel_time):
        """
        Compute residuals relative to all percentile curves.
        """
        distance = np.asarray(distance)
        travel_time = np.asarray(travel_time)

        preds = self.predict(distance)

        residuals = {}

        for col in preds.columns:
            if col.startswith("tt_p"):
                residuals[f"QC_tt_res_{col}"] = travel_time - preds[col]

        return pd.DataFrame(residuals)

    # ---------------------------------------------------------------------
    # Bounds (useful for QC)
    # ---------------------------------------------------------------------
    def compute_bounds(self, distance, p_low=1, p_high=99):
        """
        Return lower and upper travel-time bounds.
        """
        distance = np.asarray(distance)

        lower = self.p_funcs[f"tt_p{p_low}"](distance)
        upper = self.p_funcs[f"tt_p{p_high}"](distance)

        return lower, upper

    # ---------------------------------------------------------------------
    # Sigma-based bounds
    # ---------------------------------------------------------------------
    def compute_sigma_bounds(self, distance, k=3.0):
        """
        Compute bounds using median ± k*sigma.
        """
        distance = np.asarray(distance)

        median = self.p_funcs["tt_p50"](distance)
        #check nans in median
        sigma = self.std_func(distance)
        sigma = np.abs(sigma)                  # ensure positive


        lower = median - k * sigma
        upper = median + k * sigma

        return lower, upper

    # ---------------------------------------------------------------------
    # Classification (QC)
    # ---------------------------------------------------------------------
    def classify(
        self,
        distance,
        travel_time,
        method="percentile",
        p_low=1,
        p_high=99,
        k=3.0,
        return_bounds=False
    ):
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

    # ---------------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------------
    def save(self, filepath):
        """
        Save model to disk.
        """
        if filepath.endswith(".csv"):
            self.model_df.to_csv(filepath, index=False)
        elif filepath.endswith(".parquet"):
            self.model_df.to_parquet(filepath, index=False)
        else:
            raise ValueError("Unsupported format.")

    @classmethod
    def load(cls, filepath):
        """
        Load model from disk.
        """
        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
        elif filepath.endswith(".parquet"):
            df = pd.read_parquet(filepath)
        else:
            raise ValueError("Unsupported format.")

        return cls(df)
    
class MultiTravelTimeModel:
    """
    Wrapper for multiple TravelTimeModel objects, one per phase.
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
                self.models[phase] = TravelTimeModel(df_phase)
            except:
                print(f"Warning: Failed to build model for phase {phase}. Skipping.")

    # ---------------------------------------------------------------------
    # Per-phase access
    # ---------------------------------------------------------------------
    def get_model(self, phase):
        if phase not in self.models:
            raise ValueError(f"No model for phase {phase}")
        return self.models[phase]

    # ---------------------------------------------------------------------
    # Prediction
    # ---------------------------------------------------------------------
    def predict(self, phase, distance: np.ndarray) -> pd.DataFrame:
        return self.get_model(phase).predict(distance)

    # ---------------------------------------------------------------------
    # Residuals
    # ---------------------------------------------------------------------
    def compute_residuals(self, phase, distance, travel_time) -> pd.DataFrame:
        return self.get_model(phase).compute_residuals(distance, travel_time)

    # ---------------------------------------------------------------------
    # Percentile bounds
    # ---------------------------------------------------------------------
    def compute_bounds(self, phase, distance, p_low=1, p_high=99):
        return self.get_model(phase).compute_bounds(distance, p_low, p_high)

    # ---------------------------------------------------------------------
    # Sigma-based bounds
    # ---------------------------------------------------------------------
    def compute_sigma_bounds(self, phase, distance, k=3.0):
        return self.get_model(phase).compute_sigma_bounds(distance, k=k)

    # ---------------------------------------------------------------------
    # Classification
    # ---------------------------------------------------------------------
    def classify(
        self,
        phase,
        distance,
        travel_time,
        method="percentile",
        p_low=1,
        p_high=99,
        k=3.0
    ):
        return self.get_model(phase).classify(
            distance,
            travel_time,
            method=method,
            p_low=p_low,
            p_high=p_high,
            k=k
        )

    # ---------------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------------
    def save(self, filepath):
        """
        Save all phase models to a single file.
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
    def load(cls, filepath):
        """
        Load multi-phase model from file.
        """
        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
        elif filepath.endswith(".parquet"):
            df = pd.read_parquet(filepath)
        else:
            raise ValueError("Unsupported format. Use .parquet or .csv")

        if "phase" not in df.columns:
            raise ValueError("Loaded model must contain 'phase' column.")

        return cls(df)



class TravelTimeQC:
    """
    Build a TravelTimeModel from raw picks, preserving all original rows.
    """

    def __init__(self, df: pd.DataFrame, distance_col: str, tt_col: str, phase: str):
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
    def remove_xy_outliers_mahalanobis(x, y, threshold=3):
        xy = np.vstack([x, y]).T
        cov = np.cov(xy, rowvar=False)
        mean = np.mean(xy, axis=0)

        diff = xy - mean
        inv_cov = np.linalg.pinv(cov)

        md = np.sqrt(np.sum(diff @ inv_cov * diff, axis=1))
        return md <= threshold

    def clean_data(self,
               use_global=True,
               use_mahalanobis=False,
               mahalanobis_threshold=3):
        """
        Build a mask for CLEAN data used in model building.
        DOES NOT remove rows from original dataset.
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

    def compute_global_mask(self, k_override=None):
        """
        Compute mask of points consistent with global trend.
        DOES NOT remove data globally.
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
    def build_bins(self, n_bins=100, dmin=0, dmax=30e3, alpha=3.0):
        """
        Smooth nonlinear binning using power-law stretching.

        alpha > 1 → more resolution at large distances (log-like)
        alpha = 1 → linear
        alpha < 1 → more resolution at small distances
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
        min_points_per_bin=5,
        percentiles=(1, 25, 50, 75, 99),
    ):
        """
        Build TravelTimeModel using binned percentiles.
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
                    "dist_min": self.bins[i],
                    "dist_max": self.bins[i + 1],
                    "distance_center": centers[i],
                    "count": np.sum(mask),
                }

                # direct travel-time percentiles
                for p in percentiles:
                    row[f"tt_p{p}"] = np.percentile(t_bin, p)

                # robust sigma around median
                median = row["tt_p50"]
                row["sigma"] = 1.4826 * np.median(np.abs(t_bin - median))

            else:
                row = {
                    "dist_min": self.bins[i],
                    "dist_max": self.bins[i + 1],
                    "distance_center": centers[i],
                    "count": 0,
                }
                for p in percentiles:
                    row[f"tt_p{p}"] = np.nan
                row["sigma"] = np.nan

            rows.append(row)

        model_df = pd.DataFrame(rows)


        return TravelTimeModel(model_df)

    def attach_zscore(self, model):
        df = self.df_full.copy()

        valid_mask = (
            (~df[self.distance_col].isna()) &
            (~df[self.tt_col].isna()) &
            (df["phase"] == self.phase)
        )

        x = df.loc[valid_mask, self.distance_col].values
        y = df.loc[valid_mask, self.tt_col].values

        # Use model prediction (clean + consistent)
        preds = model.predict(x)

        mu = preds["tt_p50"].values
        sigma = preds["sigma"].values

        # Avoid division by zero / negative sigma
        sigma = np.where(np.abs(sigma) < 1e-12, np.nan, np.abs(sigma))

        z = (y - mu) / sigma

        df.loc[valid_mask, "tt_zscore"] = z

        return df


    # ---------------------------------------------------------------------
    # Attach QC features (uses model — very important separation)
    # ---------------------------------------------------------------------
    def attach_qc_features(self, model, classify=None):
        """
        Add residuals and QC info to the original DataFrame using the model.
        Preserves all original rows; NaN rows will have NaN residuals/QC flags.
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

class MultiPhaseTravelTimeQC:
    """
    Modular QC for multiple seismic phases.
    Wraps multiple TravelTimeQC objects internally and provides unified API.
    """

    DEFAULT_PHASES = ["P", "S", "Pn", "Sn", "Pg", "Sg"]

    def __init__(self, df: pd.DataFrame, distance_col="linear_hyp_distance", tt_col="travel_time",
                 phases=None):
        self.df = df.copy()
        self.distance_col = distance_col
        self.tt_col = tt_col
        self.phases = phases or self.DEFAULT_PHASES

        # Internal TravelTimeQC objects keyed by phase
        self.qc_objects = {}
        self.models = {}
        self.df_qc_all = pd.DataFrame()

        # Initialize QC objects for each phase
        for phase in self.phases:
            df_phase = df[df["phase"] == phase].copy()
            if not df_phase.empty:
                self.qc_objects[phase] = TravelTimeQC(df_phase, distance_col, tt_col, phase)

    # ---------------------- Cleaning ----------------------
    def clean_data(self,
               use_global=True,
               use_mahalanobis=False,
               mahalanobis_threshold=3):
        """
        Apply cleaning per phase.
        """

        for qc in self.qc_objects.values():
            qc.clean_data(
                use_global=use_global,
                use_mahalanobis=use_mahalanobis,
                mahalanobis_threshold=mahalanobis_threshold
            )

    # ---------------------- Binning ----------------------
    def build_bins(self, n_bins=100, dmin=0, dmax=30e3,alpha=3.0):
        """Build distance bins per phase."""
        for qc in self.qc_objects.values():
            qc.build_bins(n_bins=n_bins, dmin=dmin, dmax=dmax,
                          alpha=alpha)

    # ---------------------- Build Models ----------------------
    def build_models(self, min_points_per_bin=5, percentiles=(1,25,50,75,99)):
        """Build TravelTimeModel for each phase."""
        for phase, qc in self.qc_objects.items():
            try:
                self.models[phase] = qc.build_model(min_points_per_bin=min_points_per_bin,
                                                percentiles=percentiles)
            except Exception as e:
                print(f"Warning: Failed to build model for phase {phase}. Error: {e}")
        return self.models
        

    def attach_zscore(self):
        """
        Compute and attach travel-time z-scores for all phases.
        Uses each phase's model and the existing TravelTimeQC.attach_zscore.
        Returns a concatenated DataFrame with a 'tt_zscore' column.
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

    # ---------------------- Attach QC Features ----------------------
    def attach_qc_features(self, classify=None):
        """Attach residuals and QC information for all phases."""
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

    # ---------------------- Save Models (Concatenated) ----------------------
    def save_models_combined(self, filepath):
        """Concatenate all TravelTimeModel DataFrames and save as one file."""
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
            print(f"Saved combined model to {filepath}")
        else:
            print("No models to save.")

    # ---------------------- Save QC DataFrame ----------------------
    def save_qc_dataframe(self, filepath):
        """Save concatenated QC DataFrame."""
        if filepath.endswith(".parquet"):
            self.df_qc_all.to_parquet(filepath, index=False)
        elif filepath.endswith(".csv"):
            self.df_qc_all.to_csv(filepath, index=False)
        else:
            raise ValueError("Unsupported format. Use .parquet or .csv")

    # ---------------------- Residuals ----------------------
    def compute_residuals(self, phase, distance=None, travel_time=None):
        """Compute residuals relative to all percentile curves for a specific phase."""
        model = self.models.get(phase)
        if model is None:
            raise ValueError(f"No model for phase {phase}")
        qc = self.qc_objects[phase]
        distance = distance or qc.d_clean
        travel_time = travel_time or qc.t_clean
        return model.compute_residuals(distance, travel_time)

    # ---------------------- Bounds ----------------------
    def compute_bounds(self, phase, distance=None, p_low=1, p_high=99):
        """Compute percentile bounds for a specific phase."""
        model = self.models.get(phase)
        if model is None:
            raise ValueError(f"No model for phase {phase}")
        qc = self.qc_objects[phase]
        distance = distance or qc.d_clean
        return model.compute_bounds(distance, p_low, p_high)

    # ---------------------- Sigma Bounds ----------------------
    def compute_sigma_bounds(self, phase, distance=None, k=3.0):
        """Compute median ± k*sigma bounds for a specific phase."""
        model = self.models.get(phase)
        if model is None:
            raise ValueError(f"No model for phase {phase}")
        qc = self.qc_objects[phase]
        distance = distance or qc.d_clean
        return model.compute_sigma_bounds(distance, k=k)

    # ---------------------- Classification ----------------------
    def classify(self, phase, distance=None, travel_time=None, p_low=1, p_high=99):
        """Classify picks as inside/outside bounds for a specific phase."""
        model = self.models.get(phase)
        if model is None:
            raise ValueError(f"No model for phase {phase}")
        qc = self.qc_objects[phase]
        distance = distance or qc.d_clean
        travel_time = travel_time or qc.t_clean
        return model.classify(distance, travel_time, p_low=p_low, p_high=p_high)

if __name__ == "__main__":
    import pandas as pd
    import os

    network = "TAP"

    df = pd.read_parquet(f"/groups/igonin/ecastillo/UTDQuake/picks/network={network}.parquet")
    
    print(len(df))

    multi_qc = MultiPhaseTravelTimeQC(df)
    multi_qc.build_bins(n_bins=100, dmin=0.1, dmax=30e3)
    models = multi_qc.build_models(min_points_per_bin=5)
    df_qc_all = multi_qc.attach_qc_features()

    print(models)
    print(len(df_qc_all))

    models_output = f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/results/qc/network={network}.csv"
    data_output = f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/results/picks/network={network}.csv"

    os.makedirs(os.path.dirname(models_output), exist_ok=True)
    os.makedirs(os.path.dirname(data_output), exist_ok=True)

    multi_qc.save_models_combined(models_output)
    multi_qc.save_qc_dataframe(data_output)


    
    # qc = TravelTimeQC(df, distance_col="linear_hyp_distance", tt_col="travel_time", phase="P")
    # # qc.clean_data()
    # qc.build_bins( dmin=0.1, dmax=20e3, n_bins=100)
    # model = qc.build_model()
    # df_qc = qc.attach_qc_features(model)

    # output = f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/network={network}_travel_time_qc.csv"
    # model.save(output)

    # print(model.model_df)
    # print(df_qc)
