import sys
lib = None
lib = "/home/edc240000/UTDQuake"
if lib is not None:
    sys.path.append(lib)
    
    
lib = None
lib = "/home/edc240000/UTDQuake"
if lib is not None:
    sys.path.append(lib)
import pandas as pd
from utdquake.core.event.events import Events
from utdquake.core.event.stations import Stations
import datetime as dt
import numpy as np
from utdquake.core.dataset.window import EQWindow
import matplotlib.pyplot as plt
import random

stations_path = "/home/edc240000/UTDQuake/examples/custom_events/stations.csv"
ev_path = "/home/edc240000/UTDQuake/examples/custom_events/origin.csv"
picks_path = "/home/edc240000/UTDQuake/examples/custom_events/picks.db"
examples = 1000


stations = pd.read_csv(stations_path)
ev = pd.read_csv(ev_path)


stations = Stations(stations,xy_epsg="EPSG:3116",author="TexNet")
events = Events(ev,xy_epsg="EPSG:3116",author="X") ### Load all events you want to use (1 month for example)

for i in range(examples):
    events_example = events.copy().query(...) ## Filter your events considering what you want for your example
    events_stats = events_example.data.describe() # stats of your events in your example
    
    picks = events.get_picks(picks_path=picks_path,author="manual",
                         stations=stations)
    picks.dropna(subset=["utdq_distance"])
    
    
    len_picks_before_artificial = len(picks)
    picks.add_artificial_picks(events=events,
                           distances=[random.uniform(0, 60) for _ in range(10)],
                           phase_type=["P","S"])

    len_picks_before_remove = len(picks)
    picks.remove_phases_randomly(keep_ratio_p=0.8,keep_ratio_s=0.5)

    eqw = EQWindow(max_length=...) # select randomly tha maximum length (this will vary)
    eqw.add_picks(picks)
    eqw.add_noise(stations)
    len_picks_after_noise = len(eqw.picks)
    
    stats = eqw.get_stats() # stats of your picks
    
    ## at this momeent you have a lot to save related to metadata
    ## # events_stats  (from events)
    ## # len_picks_before_artificial
    ## # len_picks_before_remove
    ## # len_picks_after_noise
    ## # stats (from picks)
    ## you need to merge all this information in a single dataframe
    ## and save it in a csv file for each example in your loop
    
    
    ## you can save the window dataframe in your hdf file too in each iteration
    
    # window = eqw.get_window()




