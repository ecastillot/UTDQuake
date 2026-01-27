import pandas as pd
import os

networks_path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/cleaning/networks.csv"
df = pd.read_csv(networks_path)

print(len(df[(df["Score"]==5) & (df["Continent"]=="North America")]))

print(len(df))
exit()


df = df[df["Score"]>=3]
df = df.sort_values("Score", ascending=False)

original_folder_bank = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test"

for idx, row in df.iterrows():
    network = row["Network"]
    old_network_path = f"{original_folder_bank}/{network}"
    new_network_path = f"/groups/igonin/ecastillo/UTDBank/{network}"
    msg = f"mv {old_network_path} {new_network_path}"
    # os.system(msg)
    print(msg)
# print(df)