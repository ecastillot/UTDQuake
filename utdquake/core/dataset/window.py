# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-03-08 20:20:52
#  * @modify date 2025-03-08 20:20:52
#  * @desc [description]
#  */
import math
import random
import numpy as np
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
from utdquake.core.event.picks import Picks

def get_pick_type(row):
            
    if (row.author == "utdquake") and (row["utdq_real"] == True):
        return f'a'
    elif (row.author == "utdquake") and (row["utdq_real"] == False):
        return f'n'
    else:
        return f'o'

class EQWindow(object):
    def __init__(self, max_length=500, keep_order=False) -> None:
        """
        Initialize the EQWindow class with mandatory and optional attributes.
        
        Parameters:
        - max_length (int, optional): Maximum length of the window in seconds. Default is 500.
        - keep_order (bool, optional): If True, ensures that the order of events in your picks is preserved. Default is False.

        """
        self.max_length = max_length
        self.keep_order = keep_order
        self.window = pd.DataFrame(columns= ['ev_id', 'network', 'station', 'time', 'phase_hint'])
    
    @property
    def picks(self):
        """
        Get the picks in the EQWindow instance.
        Returns:
        - picks (Picks): A Picks instance containing seismic phase picks.
        """
        
        if self.window.empty:
            return print("No picks in the window")
        
        picks = Picks(data=self.window,
                      author="utdquake")
        return picks
    
    @property
    def ev_ids(self):
        """
        Get the events in the EQWindow instance.

        Returns:
        - events (Events): An Events instance containing event data.
        """
        if self.window.empty:
            return print("No events in the window")
        
        ev_ids = self.window["ev_id"].dropna().unique()
        return ev_ids
    
    @property
    def n_events(self):
        """
        Get the number of events in the EQWindow instance.

        Returns:
        - n_events (int): The number of unique events in the window.
        """
        if self.window.empty:
            return 0
        
        return len(self.ev_ids)
    
    @property
    def _stats_real_artificial_picks_stats(self):
        """
        Get the number of artificial picks in the EQWindow instance.
        Returns:
        - dict_stats (dict): A dictionary containing the number of artificial picks.
        """
        
        if self.window.empty:
            return 0
        
        p_picks = self.window[self.window["phase_hint"] == "P"]
        s_picks = self.window[self.window["phase_hint"] == "S"]
        
        n_real_artificial_p_picks = len(p_picks[(p_picks["utdq_real"] == True) \
                            & (p_picks["author"] =="utdquake")])
        n_real_artificial_s_picks = len(s_picks[(s_picks["utdq_real"] == True) \
                            & (s_picks["author"] =="utdquake")])
        n_real_artificial_picks = n_real_artificial_p_picks + n_real_artificial_s_picks
        
        dict_stats = {
            "n_real_artificial_p_picks": n_real_artificial_p_picks,
            "n_real_artificial_s_picks": n_real_artificial_s_picks,
            "n_real_artificial_picks": n_real_artificial_picks}
        
        return dict_stats
    
    @property
    def _stats_real_original_picks(self):
        """
        Get the number of original picks in the EQWindow instance.
        Returns:
        - dict_stats (dict): A dictionary containing the number of original picks.
        """
        if self.window.empty:
            return 0
        
        p_picks = self.window[self.window["phase_hint"] == "P"]
        s_picks = self.window[self.window["phase_hint"] == "S"]
        
        n_real_original_p_picks = len(p_picks[(p_picks["utdq_real"] == True) \
                            & (p_picks["author"] !="utdquake")])
        n_real_original_s_picks = len(s_picks[(s_picks["utdq_real"] == True) \
                            & (s_picks["author"] !="utdquake")])
        n_real_original_picks = n_real_original_p_picks + n_real_original_s_picks
        
        dict_stats = {
            "n_real_original_p_picks": n_real_original_p_picks,
            "n_real_original_s_picks": n_real_original_s_picks,
            "n_real_original_picks": n_real_original_picks}
        
        return dict_stats
    
    @property
    def _stats_real_picks(self):
        """
        Get the number of real picks in the EQWindow instance.
        Returns:
        - dict_stats (dict): A dictionary containing the number of real picks.
        """
        if self.window.empty:
            return 0
        stats_real_original_picks = self._stats_real_original_picks
        stats_real_artificial_picks = self._stats_real_artificial_picks_stats
        stats_real_picks = stats_real_original_picks["n_real_original_picks"] + \
                        stats_real_artificial_picks["n_real_artificial_picks"]
        stats_real_picks = {"n_real_picks": stats_real_picks}
        return stats_real_picks | stats_real_original_picks | stats_real_artificial_picks
    
    @property
    def n_noise_picks(self):
        
        if self.window.empty:
            return 0
        return len(self.window[self.window["utdq_real"] == False])
    
    @property
    def n_real_picks(self):
        """
        Get the number of real picks in the EQWindow instance.
        Returns:
        - n_real_picks (int): The number of real picks in the window.
        """
        
        if self.window.empty:
            return 0
        
        return self._stats_real_picks["n_real_picks"]
    
    @property
    def n_real_artificial_picks(self):
        """
        Get the number of artificial picks in the EQWindow instance.
        Returns:
        - n_real_artificial_picks (int): The number of artificial picks in the window.
        """
        
        if self.window.empty:
            return 0
        
        return self._stats_real_artificial_picks_stats["n_real_artificial_picks"]
    
    @property
    def n_real_original_picks(self):
        """
        Get the number of original picks in the EQWindow instance.
        Returns:
        - n_real_original_picks (int): The number of original picks in the window.
        """
        
        if self.window.empty:
            return 0
        
        return self._stats_real_original_picks["n_real_original_picks"]
    @property
    def n_real_artificial_p_picks(self):
        """
        Get the number of artificial P picks in the EQWindow instance.
        Returns:
        - n_real_artificial_p_picks (int): The number of artificial P picks in the window.
        """
        
        if self.window.empty:
            return 0
        
        return self._stats_real_artificial_picks_stats["n_real_artificial_p_picks"]
    @property
    def n_real_artificial_s_picks(self):
        """
        Get the number of artificial S picks in the EQWindow instance.
        Returns:
        - n_real_artificial_s_picks (int): The number of artificial S picks in the window.
        """
        
        if self.window.empty:
            return 0
        
        return self._stats_real_artificial_picks_stats["n_real_artificial_s_picks"]
    @property
    def n_real_original_p_picks(self):
        """
        Get the number of original P picks in the EQWindow instance.
        Returns:
        - n_real_original_p_picks (int): The number of original P picks in the window.
        """
        
        if self.window.empty:
            return 0
        
        return self._stats_real_original_picks["n_real_original_p_picks"]
    @property
    def n_real_original_s_picks(self):
        """
        Get the number of original S picks in the EQWindow instance.
        Returns:
        - n_real_original_s_picks (int): The number of original S picks in the window.
        """
        
        if self.window.empty:
            return 0
        
        return self._stats_real_original_picks["n_real_original_s_picks"]
    
    def __len__(self):
        
        if self.window.empty:
            return 0
        return math.ceil(self.window["utdq_wtime"].max())
    
    def get_events_wtime(self):
        """
        Get the events and their corresponding wtime in the EQWindow instance.
        Returns:
        - events (list): A list of tuples containing event ID and wtime.
        """        
        if self.window.empty:
            raise ValueError("No events in the window")
        
        window_by_event = self.window.groupby("ev_id")
        events = []
        for ev_id, data in window_by_event.__iter__():
            new_data = data.copy()
            new_data.sort_values(by=["utdq_wtime"],ignore_index=True,
                                 inplace=True)
            first_row = new_data.iloc[0]
            event_wtime = first_row["utdq_wtime"] - first_row["utdq_time"]
            events.append((ev_id,event_wtime))
        return events 
    
    def get_stats(self):
        """
        Get the statistics of the EQWindow instance.


        Returns:
        - dict_stats (dict): A dictionary containing various statistics.
        """
        
        if self.window.empty:
            return 0
        
        dict_stats = self._stats_real_picks
        
        dict_stats = {
            "window_length": len(self),
            "n_events": self.n_events,
            "n_real_picks": self.n_real_picks,
            "n_noise_picks": self.n_noise_picks,
            "n_real_original_picks": self.n_real_original_picks,
            "n_real_artificial_picks": self.n_real_artificial_picks,
            "n_real_original_p_picks": self.n_real_original_p_picks,
            "n_real_original_s_picks": self.n_real_original_s_picks,
            "n_real_artificial_p_picks": self.n_real_artificial_p_picks,
            "n_real_artificial_s_picks": self.n_real_artificial_s_picks,
        }
        
        # if events is not None:
        
        return dict_stats
    
    def add_picks(self, picks):
        """
        Add picks to the EQWindow instance.

        Parameters:
        - picks (Picks): A Picks instance containing seismic phase picks.
        """
        wdata = []
        origin_time = 0
        delta = self.max_length/(len(picks.split_by_event()))
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
                endtime = self.max_length - data["utdq_time"].max() - data["utdq_time"].max()/100
            
            
            if starttime > endtime:
                print(f"Error: starttime > endtime... skipping event {event_id}")
                continue
            
            origin_time = np.random.uniform(starttime,endtime)
            
            data["utdq_wtime"] = data["utdq_time"] + origin_time
            # print(data)
            wdata.append(data)
        wdata = pd.concat(wdata)
        
        
        
        wdata["utdq_pick_type"] = wdata.apply(get_pick_type, axis=1)
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
        
        random_floats = [random.uniform(0, self.max_length) for _ in range(len(noise))]
        random_phases = np.random.choice(['P', 'S'], size=len(noise))
        
        noise["utdq_wtime"] = random_floats
        noise["phase_hint"] = random_phases
        noise["utdq_real"] = False
        noise["author"] = "utdquake"
        
        min_distance = self.window["utdq_distance"].min()
        max_distance = self.window["utdq_distance"].max()
        noise["utdq_distance"] = np.random.uniform(min_distance, max_distance, size=len(noise))
        noise["utdq_azimuth"] = np.random.uniform(0, 360, size=len(noise)) 
        noise["utdq_bazimuth"] = noise["utdq_azimuth"].apply(lambda x: (x + 180) % 360)
        
        
        noise = noise[["network", "station", "utdq_wtime", "phase_hint", "utdq_real",
                        "utdq_distance", "utdq_azimuth", "utdq_bazimuth", "author"]]
        wdata =  pd.concat([self.window, noise])
        wdata["utdq_pick_type"] = wdata.apply(get_pick_type, axis=1)
        self.window = wdata
    def get_window(self):
        """
        Get the EQWindow for a given event.

        """
        return self.window
    