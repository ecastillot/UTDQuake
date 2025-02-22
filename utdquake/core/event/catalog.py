# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-02-22 13:34:18
#  * @modify date 2025-02-22 13:34:18
#  * @desc [description]
#  */
import pandas as pd
from .stations import Stations
from .events import Events

def read_catalog(events_path,stations_path,picks_path,
                 xy_epsg,author="UTDQuake") -> dict:
    """
    Load earthquake data from SQLite databases and return a dictionary of objects.

    Args:
        events_path (str): The path to the SQLite database file containing event data.
        stations_path (str): The path to the SQLite database file containing station data.
        picks_path (str): The path to the SQLite database file containing pick data.

    Returns:
        dict: A dictionary containing the loaded event, station, and pick data.

    Notes:
        - The `Events`, `Stations`, and `Picks` classes must be defined elsewhere in your code to handle the loaded data.
    """
    # Load event, station, and pick data from the SQLite databases
    events = pd.read_csv(events_path)
    events = Events(events,xy_epsg=xy_epsg,author=author)
    
    stations = pd.read_csv(stations_path)
    stations = Stations(stations,xy_epsg=xy_epsg,author=author)
    
    picks = events.get_picks(picks_path,stations=stations,author=author)

    stations.select_data(rowval={"sta_id":picks.stations})
    catalog = Catalog(events,stations,picks)
    return catalog

class Catalog():
    """
    A class representing a catalog of earthquake events with associated stations and picks.
    """

    def __init__(self, events, stations) -> None:
        """
        Initialize the Catalog instance.

        Parameters:
        - events (Events): An Events object containing event data.
        - stations (Stations): A Stations object containing station data.
        - picks (Picks): A Picks object containing pick data.
        """
        self.events = events
        
        
        self.stations = stations

    def __str__(self) -> str:
        """Return a string representation of the Catalog instance."""
        msg = f"Catalog | {self.events.__len__()} events, {self.stations.__len__()} stations, {self.picks.__len__()} picks"
        return msg
    
    
# events = pd.read_csv(events_path)
#     events = Events(events,xy_epsg=xy_epsg,author=author)
#     picks = events.get_picks(picks_path,author=author)
    
#     stations = pd.read_csv(stations_path)
#     stations = Stations(stations,xy_epsg=xy_epsg,author=author)
#     stations.select_data(rowval={"sta_id":picks.stations})

#     catalog = Catalog(events,stations,picks)
#     return catalog
