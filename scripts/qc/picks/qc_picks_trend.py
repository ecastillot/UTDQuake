import pandas as pd
from utdquake.qc.phase_trend import (
                                    PhaseTrendConfig,
                                    apply_phase_trend_qc)
from utdquake.qc.plot import plot_travel_time_qc


df = pd.read_parquet("/groups/igonin/ecastillo/UTDQuake/picks/network=TAP.parquet")


ptc = PhaseTrendConfig()
gd_df,gt,lt,log = apply_phase_trend_qc(df.copy(), ptc,
                                       apply_global=True,
                                        apply_local=False,
                                        debug=True)
# bd_df by resource_id
bd_df = df[~df["resource_id"].isin(gd_df["resource_id"])]

# bd_df = pd.DataFrame(columns=["phase",
#                               "linear_hyp_distance",
#                               "travel_time"])  # Empty DataFrame for bad picks since we're not applying local QC
# bd_df = df[~df.index.isin(gd_df.index)]

# print(gd_df)
# exit()
# print(lt.models)


save_path = "/groups/igonin/ecastillo/utdquake/scripts/qc/picks/3qc_picks.png"
plot_travel_time_qc(gd_df,bd_df,save_path=save_path, 
            global_models=gt.models, local_models=lt.models)
