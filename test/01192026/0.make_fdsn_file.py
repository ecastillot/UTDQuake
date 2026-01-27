from utdquake.core.cache import get_all_dataset
import pandas as pd
from utdquake.core.config import FDSN_CSV
from obspy.clients.fdsn import Client

client = Client("USGS")
contributors = list(client.services["available_event_contributors"])
usgs = pd.DataFrame(contributors, columns=["contributor"])
usgs["agency"] = "USGS"
usgs["url"] = "http://earthquake.usgs.gov"


path  = "/groups/igonin/ecastillo/utdquake/data/progress_events.csv"
df = pd.read_csv(path)
df = df.drop_duplicates(subset=["agency","provider","contributor"], 
                        keep="last",ignore_index=True)

df = df.rename(columns={"provider":"url"})
# if contributor is NaN, fill with agency
df["contributor"] = df["contributor"].fillna(df["agency"])
# add a note for JAPAN
df.loc[df["agency"]=="JAPAN","notes"] = "No FDSN web service available."

df = df[["agency","contributor","url","notes"]]


df = pd.concat([df,usgs],ignore_index=True)
df = df.sort_values(by=["agency","contributor","notes"],ignore_index=True)

df.to_csv("/groups/igonin/ecastillo/utdquake/utdquake/core/.fdsn.csv",
          index=False)