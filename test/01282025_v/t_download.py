from utdquake.core.download import download_utdquake
from utdquake.core.load import load_utdquake

local_path = "/groups/igonin/ecastillo/test"
# download_utdquake(local_path,networks="RSNC")

bank = load_utdquake(network="RSNC")

print(bank)

