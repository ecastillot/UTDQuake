import os
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

class PhaseTrendQC:

    def __init__(self, nbins=12, min_points_per_bin=20):

        self.nbins = nbins
        self.min_points_per_bin = min_points_per_bin

        self.bin_edges = None
        self.bin_models = None

    def build_bins(self,dmin=0.001, dmax=40000):
        self.bin_edges = np.logspace(
            np.log10(dmin),
            np.log10(dmax),
            self.nbins + 1
        )

    def assign_bins(self, distance):


        if self.bin_edges is None:
            raise ValueError("Call build_bins() before assigning bins.")

        print(min(distance), max(distance))
        print(self.bin_edges)

        return pd.cut(distance, self.bin_edges, 
                      labels=False, include_lowest=True)

    def fit(self, distance, time):

        df = pd.DataFrame({
            "distance": distance,
            "time": time
        })
        df["bin"] = self.assign_bins(distance)
        df = df.dropna(subset=["bin"])
        df["bin"] = df["bin"].astype(int)

        bin_models = []
        predicted_time = np.full(len(df), np.nan)
        sigma_time_bin = np.full(len(df), np.nan)
        dt_local_trend = np.full(len(df), np.nan)

        for b, group in df.groupby("bin"):

            if len(group) < self.min_points_per_bin:
                print(f"Bin {b} has only {len(group)} points, skipping.")
                continue

            idx = group.index

            d = group["distance"].values.reshape(-1,1)
            t = group["time"].values

            model = LinearRegression().fit(d, t)

            a = model.coef_[0]
            b0 = model.intercept_

            t_pred = model.predict(d)

            dt = t - t_pred

            mad = np.median(np.abs(dt - np.median(dt)))
            sigma = 1.4826 * mad

            predicted_time[idx] = t_pred
            sigma_time_bin[idx] = sigma
            dt_local_trend[idx] = dt

            bin_models.append({
                "bin": b,
                "bin_min": self.bin_edges[b],
                "bin_max": self.bin_edges[b+1],
                "slope": a,
                "intercept": b0,
                "sigma_time": sigma,
                "n": len(group)
            })

        self.bin_models = pd.DataFrame(bin_models)

        df["predicted_travel_time"] = predicted_time
        df["dt_local_trend"] = dt_local_trend
        df["sigma_time_bin"] = sigma_time_bin

        df["n_sigma_local"] = df["dt_local_trend"] / df["sigma_time_bin"]

        return df
    

class MultiPhaseTrendQC:
    """
    Apply PhaseTrendQC to multiple seismic phases and store results per phase.
    """

    def __init__(self, phases=None, nbins=20, min_points_per_bin=30):
        self.phases = phases or ["P", "S", "Pn", "Pg", "Sn", "Sg"]
        self.nbins = nbins
        self.min_points_per_bin = min_points_per_bin

        # Store results per phase
        self.results = {}     # DataFrame with metrics per phase
        self.nan_results = {}     # DataFrame with metrics per phase
        self.bin_edges = {}         # bin_edges per phase
        self.bin_models = {}        # bin_models per phase

    def run(self, df, x_col="linear_hyp_distance", y_col="travel_time"):
        """
        Run PhaseTrendQC for each phase and store results.
        """
        for phase in self.phases:
            if phase != "P":
                continue
            phase_df = df[df["phase"] == phase].copy()

            # Drop NaNs
            phase_df_na = phase_df[
                phase_df[x_col].isna() | phase_df[y_col].isna()
            ]
            phase_df = phase_df.dropna(subset=[x_col, y_col])

            if phase_df.empty:
                continue

            distance = phase_df[x_col].values
            time = phase_df[y_col].values

            qc = PhaseTrendQC(nbins=self.nbins, min_points_per_bin=self.min_points_per_bin)
            qc.build_bins()  # optionally, you can pass dmin/dmax
            metrics = qc.fit(distance, time)

            # Join metrics back to phase_df
            metrics = metrics.rename(columns={"distance": "linear_hyp_distance", "time": "travel_time"})
            phase_df = phase_df.join(metrics.drop(columns=[x_col, y_col]))

            phase_df_na2 = phase_df[phase_df["n_sigma_local"].isna()]
            phase_df = phase_df[~phase_df["n_sigma_local"].isna()]

            phase_df_na = pd.concat([phase_df_na, phase_df_na2], ignore_index=True)  # Combine original NaNs with those from metrics
            phase_df = phase_df.reset_index()  # Assuming resource_id is unique and can be used as index

            # Save everything
            self.results[phase] = phase_df
            self.nan_results[phase] = phase_df_na
            self.bin_edges[phase] = qc.bin_edges
            self.bin_models[phase] = qc.bin_models

        return self.results

    def save(self, folder="phase_trend_data"):
        """
        Save all phase QC results into a folder.
        """
        os.makedirs(folder, exist_ok=True)

        for phase in self.phases:
            phase_folder = os.path.join(folder, phase)
            os.makedirs(phase_folder, exist_ok=True)

            if phase in self.results:
                self.results[phase].to_csv(os.path.join(phase_folder, "metrics.csv"), index=False)
            if phase in self.nan_results:
                self.nan_results[phase].to_csv(os.path.join(phase_folder, "nan_metrics.csv"), index=False)
            if phase in self.bin_models:
                self.bin_models[phase].to_csv(os.path.join(phase_folder, "bin_models.csv"), index=False)
            if phase in self.bin_edges:
                with open(os.path.join(phase_folder, "bin_edges.pkl"), "wb") as f:
                    pickle.dump(self.bin_edges[phase], f)

        print(f"All phase data saved in folder: {folder}")

    @classmethod
    def load(cls, folder="phase_trend_data"):
        mpqc = cls()

        for phase in os.listdir(folder):
            phase_folder = os.path.join(folder, phase)
            if not os.path.isdir(phase_folder):
                continue

            def safe_read_csv(path):
                if not os.path.exists(path) or os.path.getsize(path) == 0:
                    return pd.DataFrame()
                try:
                    return pd.read_csv(path)
                except pd.errors.EmptyDataError:
                    return pd.DataFrame()

            mpqc.results[phase] = safe_read_csv(os.path.join(phase_folder, "metrics.csv"))
            mpqc.nan_results[phase] = safe_read_csv(os.path.join(phase_folder, "nan_metrics.csv"))
            mpqc.bin_models[phase] = safe_read_csv(os.path.join(phase_folder, "bin_models.csv"))

            bin_edges_path = os.path.join(phase_folder, "bin_edges.pkl")
            if os.path.exists(bin_edges_path):
                with open(bin_edges_path, "rb") as f:
                    mpqc.bin_edges[phase] = pickle.load(f)

        print(f"All phases loaded from folder: {folder}")
        return mpqc