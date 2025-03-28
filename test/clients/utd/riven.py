import sys
lib = None
lib = "/home/edc240000/UTDQuake"
if lib is not None:
    sys.path.append(lib)

import pandas as pd
from utdquake.core.event.stations import Stations
from utdquake.core.event.catalog import read_catalog
import random


test_stations_data = pd.read_csv('/home/edc240000/riven/25032025/Updated_Networks_Stations.csv')
test_stations = Stations(test_stations_data,xy_epsg="EPSG:3116",author="Texas")
print(test_stations)
test_catalog = read_catalog(events_path='/home/edc240000/riven/25032025/cleaned_all_dec_2024_TX_EQ.csv',
                       xy_epsg="EPSG:3116",
                       stations_path='/home/edc240000/riven/25032025/Updated_Networks_Stations.csv')
test_catalog.sample(5)
print(test_catalog)



test_picks = test_catalog.get_picks(picks_path='/home/edc240000/riven/25032025/all_dec_2024_TX_picks.db',author="manual")
test_picks.dropna(subset=["utdq_distance"]) #drop picks without distance

print(test_picks)

print("Before adding artificial picks:",test_picks)

#FIRST ADD ARTIFICIAL PICKS, THEN REMOVE SOME RANDOMLY
test_picks.add_artificial_picks(events=test_catalog.events,
                           distances=[random.uniform(4.66, 124.92) for _ in range(11)], #11 stations
                           phase_type=["P","S"])
print("Adding artificial picks:", test_picks)

test_picks.remove_phases_randomly(keep_ratio_p=0.8,keep_ratio_s=0.5)
print("After removing random picks:", test_picks)
print(len(test_picks.data))