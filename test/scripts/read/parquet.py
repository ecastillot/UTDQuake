import pandas as pd
# read the parquet file

# path = "/home/edc240000/.utdquake/picks/network=tx.parquet"
path = "/groups/igonin/ecastillo/UTDQuake_DAS/stations/network=GCI.parquet"
df_ori = pd.read_parquet(path)
# print(df_ori[["travel_time_zscore"]].describe())
print(df_ori.info())
# print(df_ori.info())
# print(df_ori[["network","agency","original_events","original_p_arrivals",
#                     "original_s_arrivals",
#                     "events","p_arrivals",
#                     "s_arrivals"]])
exit()

path = "/groups/igonin/ecastillo/bck_utdq/test_021926/picks/network=uw.parquet"
df_ori = pd.read_parquet(path)
t = df_ori.query(
    'resource_id in ["quakeml:uw.anss.org/AssocArO/UW/17409843", '
    '"quakeml:uw.anss.org/AssocArO/UW/17409848"]'
)
print(t[["station","phase","time","travel_time","distance","linear_hyp_distance"]])
# print(df["url"])
# print(df_ori.info())
exit()

path_cor = "/home/edc240000/.utdquake/network/network.parquet"
df_cor = pd.read_parquet(path_cor)
cor_cols = ["network","agency","continent","url","score"]
df_cor = df_cor[cor_cols]   
df_cor = df_cor.rename(columns={"agency": "provider"})

df_ori = pd.merge(df_ori, df_cor, on="network", how="left", suffixes=("_ori", "_cor"))
print(df_ori.info())

alaska_region = (-180, -130, 50, 72)  
alaska_netwroks = ["av","ak","AEIC"]

# locate alaska networks and change the approx_lon_min, approx_lon_max, approx_lat_min, approx_lat_max to the alaska region
for network in alaska_netwroks:
    mask = df_ori["network"] == network
    df_ori.loc[mask, "approx_lon_min"] = alaska_region[0]
    df_ori.loc[mask, "approx_lon_max"] = alaska_region[1]
    df_ori.loc[mask, "approx_lat_min"] = alaska_region[2]
    df_ori.loc[mask, "approx_lat_max"] = alaska_region[3]

