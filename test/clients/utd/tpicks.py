import pandas as pd
from utdquake.core.event.picks import Picks,  read_picks,read_picks_in_chunks
import datetime as dt
from utdquake.core.database.database import load_from_sqlite

# data_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/stations.csv"
# data = pd.read_csv(data_path)
# # print(data)
# eqdata = DataFrameHelper(data,
#                         required_columns=["latitude","longitude"])
# mul_eqdata = MulDataFrameHelper([eqdata,eqdata,eqdata])
# # print(eqdata)
# # print(eqdata.__str__(True))
# # print(type(eqdata))
# # print(mul_eqdata)
# # print(mul_eqdata.__str__(True))
# # print(type(mul_eqdata))
# exit()

picks_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/picks.db"

df = load_from_sqlite(picks_path)
# print(df)
# exit()
# picks = read_picks(picks_path,author="manual",
#                    custom_params={"distance":{"condition":"<","value":0.5},
#                                   "station":{"condition":"LIKE","value":"OKAS%"}
#                                   })

# # print(picks["station"])
# print(picks)
# exit()
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
# print(picks.__str__("utdquake"))
print(picks.__str__("pandas"))
exit()

picks2 = Picks(data=df,author="manual2")
# print(picks.data.info())

# exit()
# print(picks.data)
# print(len(picks))

# print(picks.lead_pick)
# print(picks.stations)
# print(picks)
# ps_picks = picks.drop_picks_with_single_phase(inplace=True)
ps_picks = picks.drop_picks_with_single_phase()
# print(ps_picks)
# print(picks)
# exit()
# print(ps_picks.data.describe())
# print(ps_picks.data)

mulpicks = MulPicks([ps_picks,picks2])
# t = mulpicks.get_stations()
# print(t)
# t = mulpicks.get_lead_pick()
# print(type(t))
# t= mulpicks.drop_picks_with_single_phase()
# print(t)
print(mulpicks.datahelpers[0].empty)
# print(type(mulpicks.datahelpers[0]))
t = mulpicks.compare_times(author1="manual",author2="manual2")
print(t)