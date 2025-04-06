# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-03-08 20:20:52
#  * @modify date 2025-03-08 20:20:52
#  * @desc [description]
#  */
import random
import numpy as np
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt


class EQWindow(object):
    def __init__(self, length=500, keep_order=False) -> None:
        """
        Initialize the EQWindow class with mandatory and optional attributes.
        
        Parameters:
        - length (int, optional): Length of the window in seconds. Default is 500.
        - keep_order (bool, optional): If True, ensures that the order of events in your picks is preserved. Default is False.

        """
        self.length = length
        self.keep_order = keep_order
        self.window = pd.DataFrame()
        
    def add_picks(self, picks):
        """
        Add picks to the EQWindow instance.

        Parameters:
        - picks (Picks): A Picks instance containing seismic phase picks.
        """
        wdata = []
        origin_time = 0
        delta = self.length/(len(picks.split_by_event()))
        for i,pick_by_ev in enumerate(picks.split_by_event(),1):
            # print(pick_by_ev.events)
            event_id = pick_by_ev.events[0]
            data = pick_by_ev.data
            # I was trying to keep time distance buut it is challenging 
            # (there are some tricky things to keep in mind)
            # if self.keep_order:
            # data.sort_values(by=["time"],inplace=True)
            # first_pick = (data["time"].iloc[-1] + dt.timedelta(data["utdq_time"].iloc[-1])) - \
            #             (data["time"].iloc[0] + dt.timedelta(data["utdq_time"].iloc[0]))
            # first_pick = first_pick.total_seconds()
            # print(first_pick)
                # origin_time
            
            if self.keep_order:
                starttime = origin_time
                endtime = origin_time + (delta*i - origin_time)
            else:
                starttime = 0
                endtime = self.length - data["utdq_time"].max() - data["utdq_time"].max()/100
            
            
            if starttime > endtime:
                print(f"Error: starttime > endtime... skipping event {event_id}")
                continue
            
            origin_time = np.random.uniform(starttime,endtime)
            
            data["utdq_wtime"] = data["utdq_time"] + origin_time
            # print(data)
            wdata.append(data)
        wdata = pd.concat(wdata)
        wdata = wdata.sort_values(by=["utdq_wtime"],ignore_index=False)
        self.window = wdata
        
        # plt.plot(wdata["utdq_wtime"], wdata["utdq_distance"], 'o')
        # plt.show()
        # print(wdata)
    
    def add_noise(self, stations,
                  random_range=(1, 500)):
        """
        Add noise to the EQWindow instance.

        Parameters:
        - stations (Stations): A Stations instance containing station data.
        """
        n_phases = random.randint(*random_range)
        
        noise = stations.data.copy()
        sta_in_window = self.window["station"].unique()
        noise["weigth"] = noise.apply(lambda x: 1 if x["station"] in sta_in_window else 0.05, axis=1)
        
        noise = noise.sample(n_phases, weights="weigth", replace=True,ignore_index=True) 
        
        random_floats = [random.uniform(0, self.length) for _ in range(len(noise))]
        random_phases = np.random.choice(['P', 'S'], size=len(noise))
        
        noise["utdq_wtime"] = random_floats
        noise["phase_hint"] = random_phases
        noise["utdq_real"] = False
        noise["author"] = "utdquake"
        
        
        
        noise = noise[["network", "station", "utdq_wtime", "phase_hint", "utdq_real"]]
        self.window = pd.concat([self.window, noise])
        
        
        
        # print(self.window)
        # # plt.plot(self.window["utdq_wtime"], self.window["utdq_distance"], 'o')
        # plt.plot(self.window["utdq_wtime"], self.window["station"], 'o')
        # plt.show()
        # # noise = pd.DataFrame({
        # #     ""
        # #     "utdq_wtime": random_floats,
        # #     "utdq_phase": random_phases
        # # }) 
        
        # # n_phases = random.randint(range)
        # # print(stations.data)
        # # pass
    # noise2station_args: dict = {  
    #                  "range": (1, 100),  # Range of possible numbers of noise phases
    #                  "stations_range": (1, 5),  # Range of possible numbers of stations affected by noise
    #                  "priority_stations_factor": 80  # Factor for weighting the number of affected stations
    #              }    
        
    def get_window(self):
        """
        Get the EQWindow for a given event.

        """
        return self.window
    