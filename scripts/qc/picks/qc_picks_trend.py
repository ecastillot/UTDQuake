import pandas as pd
import os
from utdquake.qc.phase_trend import (
                                    PhaseTrendConfig,
                                    apply_phase_trend_qc,
                                    export_qc_run)
from utdquake.qc.plot import plot_travel_time_qc

networks = ["tx","uw","ok","nn","RSNC","nc"]

for network in networks:
    df = pd.read_parquet(f"/groups/igonin/ecastillo/UTDQuake/picks/network={network}.parquet")

    k = {
        "P": 3, "Pn": 3, "Pg": 3, "S": 3, "Sn": 3, "Sg": 3
        }
    ptc = PhaseTrendConfig(k_dict=k)
    gd_df,gt,lt,log = apply_phase_trend_qc(df.copy(), ptc,
                                            apply_global=True,
                                            apply_local=True,
                                            # apply_local=False,
                                            debug=True)


    # path = "/groups/igonin/ecastillo/utdquake/scripts/qc/picks/qc_run.json"
    # export_qc_run( path, gt, lt, ptc)

    # bd_df by resource_id
    bd_df = df[~df["resource_id"].isin(gd_df["resource_id"])]


    save_path = f"/groups/igonin/ecastillo/utdquake/scripts/qc/picks/plots/{network}.png"
    plot_travel_time_qc(gd_df,bd_df,
                        network,
                        save_path=save_path, 
                        log=log,
                        global_models=gt.models, 
                        local_models=lt.models,
                        fit_xy_limits=True
                        )
