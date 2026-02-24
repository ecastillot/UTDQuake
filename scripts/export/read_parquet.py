import pandas as pd
# read the parquet file

path = "/groups/igonin/ecastillo/bck_utdq/test_021926/events/network=RSNC.parquet"
# path = "/groups/igonin/ecastillo/bck_utdq/test_021926/picks/network=RSNC.parquet"
df_ori = pd.read_parquet(path)


# #check nan in time column
# x = df_ori["time"].isna().sum()

# print(x,"nan in time column")
# print(df_ori[df_ori["travel_time"]<0])
print(df_ori.info())


# print(df_ori.info())
# print(df_ori["resource_id_arrival"].unique())
# t = df_ori[df_ori["resource_id_arrival"].isin(["quakeml:uw.anss.org/AssocArO/UW/17409843",
#                                                "quakeml:uw.anss.org/AssocArO/UW/17409848"])]


# # path = "/groups/igonin/ecastillo/UTDQuake/picks/network=uw.parquet"
# df_ori = pd.read_parquet(path)
# # print(df["url"])
# print(df_ori.info())
# print(df_ori["resource_id_arrival"].unique())
# t = df_ori[df_ori["resource_id_arrival"].isin(["quakeml:uw.anss.org/AssocArO/UW/17409843",
#                                                "quakeml:uw.anss.org/AssocArO/UW/17409848"])]
# print(t)




