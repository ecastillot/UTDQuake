import pandas as pd
from utdquake.qc.phase_trend import (
                                    PhaseTrendConfig,
                                    GlobalTrendFilter, 
                                    LocalTrendFilter, 
                                    PhasePlotter)


df = pd.read_parquet("/groups/igonin/ecastillo/UTDQuake/picks/network=RSNC.parquet")

# df = df.dropna(subset=["linear_hyp_distance", "travel_time", "phase"])

print(df)
gt = GlobalTrendFilter()
df,rdf,log = gt.apply(df)
print(df)

config = PhaseTrendConfig()
lt = LocalTrendFilter(config)
df,r2df,log = lt.apply(df,log=log)
print(df)

#sum nan
print(df[["travel_time","linear_hyp_distance","phase"]].isna().sum())

# print(log)

# config = PhaseTrendConfig(
#     phase_order=["P", "Pn", "Pg", "S", "Sn", "Sg"],
#     k_dict={"P": 5, "Pn": 5, "Pg": 5, "S": 5, "Sn": 5, "Sg": 5},
#     degree=1,
# )

# plotter = PhasePlotter()
# fig, axes = plotter.plot_all(df, filterer.models, config)


