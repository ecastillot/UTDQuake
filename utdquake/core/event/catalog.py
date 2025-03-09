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

def read_catalog(events_path, xy_epsg, stations_path=None, author="UTDQuake") -> dict:
    """
    Load earthquake data from CSV files and return a Catalog object.

    Parameters:
    ----------
    events_path : str
        Path to the CSV file containing event data.
    xy_epsg : int
        EPSG code for coordinate transformation.
    stations_path : str, optional
        Path to the CSV file containing station data. Default is None.
    author : str, default="UTDQuake"
        Author/source of the data.

    Returns:
    -------
    Catalog
        A Catalog object containing the loaded event and station data.

    Notes:
    ------
    - The `Events` and `Stations` classes must be defined elsewhere in your code 
      to properly handle the loaded data.
    - If `stations_path` is not provided, the station data will not be loaded.
    """

    # Load event data from CSV and create an Events instance
    events = pd.read_csv(events_path)
    events = Events(events, xy_epsg=xy_epsg, author=author)

    # Load station data if a path is provided, otherwise set stations to None
    if stations_path is None:
        stations = None
    else:
        stations = pd.read_csv(stations_path)
        stations = Stations(stations, xy_epsg=xy_epsg, author=author)

    # Create and return a Catalog instance
    catalog = Catalog(events, stations)
    return catalog


class Catalog:
    """
    A class representing a catalog of earthquake events with associated stations.

    Attributes:
    -----------
    events : Events
        An instance of the Events class containing earthquake event data.
    stations : Stations, optional
        An instance of the Stations class containing station data.
    """

    def __init__(self, events, stations) -> None:
        """
        Initialize a Catalog instance.

        Parameters:
        ----------
        events : Events
            An Events object containing event data.
        stations : Stations, optional
            A Stations object containing station data. 
        """
        self.events = events
        self.stations = stations

    def __str__(self) -> str:
        """
        Return a string representation of the Catalog instance.

        Returns:
        -------
        str
            A formatted string summarizing the number of events and the presence of stations.
        """
        return f"Catalog | {len(self.events)} events, stations: {self.stations is not None}"

    def sample(self, n=1):
        """
        Return a random sample of events from the catalog.

        Parameters:
        ----------
        n : int, default=10
            Number of events to sample.

        Returns:
        -------
        pd.DataFrame
            A DataFrame containing the sampled events.
        """
        self.events.sample(n)

    def get_picks(self, picks_path, author="UTDQuake"):
        """
        Retrieve pick data associated with the events.

        Parameters:
        ----------
        picks_path : str
            Path to the file containing pick data.
        author : str, default="UTDQuake"
            Author/source of the pick data.

        Returns:
        -------
        Picks
            An instance of the Picks class containing the loaded pick data.
        """
        return self.events.get_picks(picks_path=picks_path, 
                                     stations=self.stations, 
                                     author=author)
        # self.stations.select_data(rowval={"sta_id":picks.stations})
        
    
    
    
    
# events = pd.read_csv(events_path)
#     events = Events(events,xy_epsg=xy_epsg,author=author)
#     picks = events.get_picks(picks_path,author=author)
    
#     stations = pd.read_csv(stations_path)
#     stations = Stations(stations,xy_epsg=xy_epsg,author=author)
#     stations.select_data(rowval={"sta_id":picks.stations})

#     catalog = Catalog(events,stations,picks)
#     return catalog
