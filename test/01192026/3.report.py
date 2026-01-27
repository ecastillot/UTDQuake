from utdquake.core.cache import create_report
import pandas as pd
from utdquake.core.config import FDSN_CSV

save = "/groups/igonin/ecastillo/utdquake/test/01192026/report"
x,y,z = create_report(save)
print(x)
print(y.describe().info())
print(z.describe().info())



