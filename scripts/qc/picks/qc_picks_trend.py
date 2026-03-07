import pandas as pd
from utdquake.qc.phase_trend import (
                                    PhaseTrendConfig,
                                    apply_phase_trend_qc,
                                    export_qc_run)
from utdquake.qc.plot import plot_travel_time_qc


df = pd.read_parquet("/groups/igonin/ecastillo/UTDQuake/picks/network=AUST.parquet")

k = {
    "P": 3, "Pn": 3, "Pg": 3, "S": 3, "Sn": 3, "Sg": 3
    }
ptc = PhaseTrendConfig(k_dict=k)
gd_df,gt,lt,log = apply_phase_trend_qc(df.copy(), ptc,
                                        apply_global=True,
                                        apply_local=True,
                                        debug=True)


path = "/groups/igonin/ecastillo/utdquake/scripts/qc/picks/qc_run.json"
export_qc_run( path, gt, lt, ptc)

# bd_df by resource_id
bd_df = df[~df["resource_id"].isin(gd_df["resource_id"])]


save_path = "/groups/igonin/ecastillo/utdquake/scripts/qc/picks/3qc_picks.png"
plot_travel_time_qc(gd_df,bd_df,save_path=save_path, log=log,
            global_models=gt.models, 
            local_models=lt.models,
            fit_xy_limits=True
            )
