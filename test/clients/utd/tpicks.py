import pandas as pd
from utdquake.core.event.data import DataFrameHelper,MulDataFrameHelper
from utdquake.core.database.database import load_dataframe_from_sqlite
from utdquake.core.event.picks import Picks, MulPicks, read_picks
import datetime as dt
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

# df = load_dataframe_from_sqlite(picks_path)
picks = read_picks(picks_path,author="manual",
                   custom_params={"distance":{"condition":"<","value":0.5},
                                  "station":{"condition":"LIKE","value":"OKAS%"}
                                  })

print(picks["station"])
print(picks)

exit()

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