import pandas as pd
from utdquake.core.event.data import DataFrameHelper,MulDataFrameHelper
from utdquake.core.database import load_dataframe_from_sqlite
from utdquake.core.event.event import Picks

data_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/stations.csv"
data = pd.read_csv(data_path)
# print(data)
eqdata = DataFrameHelper(data,
                        required_columns=["latitude","longitude"])
mul_eqdata = MulDataFrameHelper([eqdata,eqdata,eqdata])
# print(eqdata)
# print(eqdata.__str__(True))
# print(type(eqdata))
# print(mul_eqdata)
# print(mul_eqdata.__str__(True))
# print(type(mul_eqdata))
exit()

picks_path = "/home/emmanuel/ecastillo/dev/utdquake/test/clients/utd/custom_events/picks.db"

df = load_dataframe_from_sqlite(picks_path)
# print(df.columns)
picks = Picks(data=df)
print(picks)
# print(picks.data)
# print(len(picks))
# print(picks.lead_pick)
# print(picks.stations)
ps_picks = picks.drop_picks_with_single_phase()
print(ps_picks)
# print(ps_picks.data)