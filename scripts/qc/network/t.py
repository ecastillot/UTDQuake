import pandas as pd

import pyarrow.parquet as pq
table = pq.read_table("/groups/igonin/ecastillo/utdquake/scripts/qc/network/network.parquet")
print(table.schema)

# # Try reading the file
# df = pd.read_parquet("/groups/igonin/ecastillo/utdquake/scripts/qc/network/network.parquet")

# # Check first few rows
# print(df.head())

# # Check column types
# print(df.dtypes)

# # Check for missing or NaN values
# print(df.isna().sum())