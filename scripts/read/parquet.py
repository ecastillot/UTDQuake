import pandas as pd
# read the parquet file

path = "/groups/igonin/ecastillo/UTDQuake/network/network.parquet"
df_ori = pd.read_parquet(path)
# print(df["url"])
print(df_ori.info())

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

