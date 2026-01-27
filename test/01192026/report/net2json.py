import pandas as pd

path = "/groups/igonin/ecastillo/utdquake/test/01192026/report/network_label.csv"
data = pd.read_csv(path)
data = data[["Network","Score","Continent","Countries"]]

#no capitalize
data = data.rename(columns={"Network":"network",
                            "Score":"score",
                            "Continent":"continent",
                            "Countries":"countries"})


fdsn_path = "/groups/igonin/ecastillo/utdquake/test/01192026/report/.fdsn.csv"
fdsn = pd.read_csv(fdsn_path)
fdsn = fdsn.rename(columns={"contributor":"network"})
fdsn = fdsn[["network","agency","url"]]

data = data.merge(fdsn, on="network", how="inner")

print(data )
data.to_csv("/groups/igonin/ecastillo/utdquake/test/01192026/report/manual_report.csv",
            index=False)
# data.to_json(
#     "score.json",
#     orient="records",
#     indent=2
# )