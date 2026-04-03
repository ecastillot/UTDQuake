import os 

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from utdquake.utils.plot import plot_travel_time_qc

import pandas as pd
from utdquake.qc.travel_time import TravelTimeModel
network = "AUST"
# path = "/groups/igonin/ecastillo/UTDQuake/manifests/test/picks/network=TAP.parquet"
path = f"/groups/igonin/ecastillo/UTDQuake/picks/network={network}.parquet"
df = pd.read_parquet(path)
df.sort_values("linear_hyp_distance", inplace=True)
print(df[["phase","linear_hyp_distance","travel_time","travel_time_zscore"]].head())
    
# model_path = f"/groups/igonin/ecastillo/UTDQuake/manifests/test/qc/pick_models/network=TAP.parquet"
model_path = f"/groups/igonin/ecastillo/UTDQuake/qc/pick_models/network={network}.parquet"
load = TravelTimeModel.load(model_path)
models = load.models
fig_path = f"/groups/igonin/ecastillo/utdquake/scripts/fig/test_new_figs.png" 
plot_travel_time_qc(df, models=models, zscore_threshold=3,
            show_global_model=True,
            add_inset=True, savepath=fig_path,
            )
# plot_travel_time_qc(df, add_inset=True, savepath=fig_path)

