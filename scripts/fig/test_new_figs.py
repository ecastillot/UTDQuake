import os 

os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

from utdquake.utils.plot import plot_travel_time_qc

import pandas as pd
from utdquake.qc.travel_time import TravelTimeModel
network = "us"
path = f"/groups/igonin/ecastillo/UTDQuake/picks/network={network}.parquet"
df = pd.read_parquet(path)
    
model_path = f"/groups/igonin/ecastillo/UTDQuake/qc/pick_models/network={network}.parquet"
load = TravelTimeModel.load(model_path)
models = load.models
fig_path = f"/groups/igonin/ecastillo/utdquake/scripts/fig/test_new_figs.png" 
plot_travel_time_qc(df, models=models, zscore_threshold=2,
            add_inset=True, savepath=fig_path)
# plot_travel_time_qc(df, add_inset=True, savepath=fig_path)

