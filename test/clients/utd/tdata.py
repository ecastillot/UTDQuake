import pandas as pd
from utdquake.core.event.picks import Picks, MulPicks, read_picks,read_picks_in_chunks
import datetime as dt
from utdquake.core.event.data import DataFrameHelper
data_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/stations.csv"
data = pd.read_csv(data_path)
# data.drop(columns="latitude",inplace=True)
eqdata = DataFrameHelper(data,
                        required_columns=["latitude","longitude"],
                        date_columns=["starttime"])
# mul_eqdata = MulDataFrameHelper([eqdata,eqdata,eqdata])
# print(eqdata.__str__("utdquake"))
# eqdata = eqdata.sort_values(["station"])

print(eqdata)
# x = eqdata.select_data({"station":["PB02"]})
x = eqdata.select_data({"station":["PB02"]},inplace=True)

# x = eqdata.append(eqdata,inplace=False)
# x = eqdata.append(eqdata,inplace=True)
# x = eqdata.remove_data({"station":["PB02"]},inplace=True)

# y = eqdata.copy()
# print(type(y))

# x = eqdata.filter("elevation",900,1000,inplace=False)
# x = eqdata.filter("elevation",900,1000,inplace=True)
# print(x)
# print(type(x))
# print(eqdata)
# print(type(eqdata))


# print(eqdata)
# print(type(x))
# nx = x.append(x)
# print(nx)
# x.reset_index(inplace=True)
# print(x,"\n")
# print(eqdata)

# exit()
# eqdata.select_data({"station":["PB02"]})
# print(t)
# print(eqdata)
# print(eqdata.head(10))
# print(eqdata.required_columns)
# print(eqdata.__str__("pandas"))
# print(eqdata.empty)
# print(type(eqdata.required_columns))
# # print(eqdata.__str__(True))
# # print(type(eqdata))
# # print(mul_eqdata)
# # print(mul_eqdata.__str__(True))
# # print(type(mul_eqdata))
# exit()

# picks_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/picks.db"

# # df = load_dataframe_from_sqlite(picks_path)
# picks = read_picks(picks_path,author="manual",
#                    custom_params={"distance":{"condition":"<","value":0.5},
#                                   "station":{"condition":"LIKE","value":"OKAS%"}
#                                   })

# # print(picks["station"])
# print(picks)

# picks = read_picks_in_chunks(picks_path,author="manual",
#                              chunksize=5,
#                    custom_params={"distance":{"condition":"<","value":0.5},
#                                   "station":{"condition":"LIKE","value":"OKAS%"}
#                                   })

# for pick in picks:
#     print(pick)
#     print(pick.data)

# exit()

# print(df.columns)
picks = Picks(data=df,author="manual")
picks2 = Picks(data=df,author="manual2")
print(picks.data.info())

# exit()
# print(picks.data)
# print(len(picks))
# print(picks.lead_pick)
# print(picks.stations)
ps_picks = picks.drop_picks_with_single_phase()
print(ps_picks)
print(ps_picks.data.describe())
# print(ps_picks.data)

mulpicks = MulPicks([ps_picks,picks2])
t = mulpicks.get_stations()
print(t)
t = mulpicks.get_lead_pick()
print(t)
mulpicks.drop_picks_with_single_phase()
# t = mulpicks.compare_times(author1="manual",author2="manual2")
# print(t)