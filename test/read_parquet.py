import pandas as pd

path = "/groups/igonin/ecastillo/UTDQuake/qc/pick_models/network=TAP.parquet"
df = pd.read_parquet(path)
print(df.iloc[:10])