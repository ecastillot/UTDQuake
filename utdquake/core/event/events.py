# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-01-24 18:56:41
#  * @modify date 2025-01-24 18:56:41
#  * @desc [description]
#  */
import warnings
import pandas as pd
import datetime as dt
from .spatial  import Points
from .picks import read_picks, Picks
from .stations import Stations
from .utils import get_distance_in_dataframe

class Events(Points):
    """
    A class representing a collection of seismic events.
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the Events class with mandatory and optional attributes.

        Parameters:
        - *args: Positional arguments passed to the parent class.
        - **kwargs: Keyword arguments passed to the parent class.
        """
        # Define mandatory columns for event data
        mandatory_columns = ['ev_id', 'origin_time', 'latitude', 'longitude', 'depth', 'magnitude']
        
        # Call the parent class constructor with required and optional parameters
        super().__init__(*args, mandatory_columns=mandatory_columns, date_columns=["origin_time"], **kwargs)

    def __str__(self, extended=False) -> str:
        """
        Return a string representation of the Events instance.

        Parameters:
        - extended (bool, optional): If True, include detailed information. Defaults to False.

        Returns:
        - str: Formatted string summarizing the event data.
        """
        if extended:
            timefmt = "%Y%m%dT%H:%M:%S"
            start = self.data.origin_time.min()
            end = self.data.origin_time.max()
            region = [round(x, 2) for x in self.get_region()]
            msg = (
                f"Events | {self.__len__()} events "
                f"\n\tperiod: [{start.strftime(timefmt)} - {end.strftime(timefmt)}]"
                f"\n\tdepth : [{round(self.data.depth.min(), 2)}, {round(self.data.depth.max(), 2)}]"
                f"\n\tmagnitude : [{round(self.data.magnitude.min(), 2)}, {round(self.data.magnitude.max(), 2)}]"
                f"\n\tregion: {region}"
            )
        else:
            msg = f"Events | {self.__len__()} events "
        return msg

    def query(self, starttime=None, endtime=None, ev_ids=None, agencies=None,
              mag_lims=None, region_lims=None, general_region=None,
              region_from_src=None):
        """
        Query and filter events based on various criteria.

        Parameters:
        - starttime (datetime, optional): Start time for filtering events.
        - endtime (datetime, optional): End time for filtering events.
        - ev_ids (list, optional): List of event IDs to include.
        - agencies (list, optional): List of agencies to include.
        - mag_lims (tuple, optional): Magnitude range as (min, max).
        - region_lims (list, optional): Rectangular region limits [lon_min, lon_max, lat_min, lat_max].
        - general_region (list of tuples, optional): Polygon defining a general region [(lon, lat), ...].
        - region_from_src (tuple, optional): Source-based region definition (latitude, longitude, max_radius, max_azimuth).

        Returns:
        - Events: The filtered Events object.
        """
        self.filter("origin_time", starttime, endtime)
        if ev_ids is not None and len(self) != 0:
            self.select_data({"ev_id": ev_ids})
        if agencies is not None and len(self) != 0:
            self.select_data({"agency": agencies})
        if mag_lims is not None and len(self) != 0:
            self.filter("magnitude", start=mag_lims[0], end=mag_lims[1])
        if region_lims is not None and len(self) != 0:
            self.filter_rectangular_region(region_lims)
        if general_region is not None and len(self) != 0:
            self.filter_general_region(general_region)
        if region_from_src is not None and len(self) != 0:
            lat, lon, r_max, az_max = region_from_src
            self.filter_by_r_az(latitude=lat, longitude=lon, r=r_max, az=az_max)
        return self

    def get_picks(self, picks_path, stations=None, author="UTDQuake",debug=False):
        """
        Load and return picks data associated with events.

        Parameters:
        ----------
        picks_path : str
            Path to the picks data file.
        stations : Stations, optional
            An instance of the Stations class containing station information. 
            If provided, the function merges station data with pick data.
        author : str, default="UTDQuake"
            Author/source of the picks data.

        Returns:
        -------
        Picks
            An instance of the Picks class containing the loaded picks data.
        """
        
        # Return empty Picks instance if no event data is available
        if self.data.empty:
            return Picks(data=pd.DataFrame(), author=author)

        # Read picks data from the provided file path
        picks = read_picks(picks_path)
        
        # Store the original columns for later use
        out_columns = picks.columns.to_list()

        # If station data is provided, merge it with pick data
        if stations is not None:
            if isinstance(stations, Stations):
                # Define columns from the event data that need to be merged
                src_columns = ["ev_id", "latitude", "longitude", "depth", "origin_time"]
                picks = pd.merge(picks, self.data[src_columns], on="ev_id")
                
                # Rename event source columns to avoid conflicts
                picks = picks.rename(columns={col: f"src_{col}" for col in src_columns if col != "ev_id"})

                # Copy station data to avoid modifying the original dataset
                stations_data = stations.data.copy()

                # Merge station data with picks
                picks = pd.merge(
                    picks, stations_data,
                    on=["network", "station"],
                    how="left",
                    suffixes=("", "_station")
                )

                # Rename station columns for clarity
                sta_columns = ["latitude", "longitude", "elevation"]
                picks = picks.rename(columns={col: f"sta_{col}" for col in sta_columns})

                # Check for missing station coordinates and issue a warning
                if picks["sta_latitude"].isnull().sum() > 0:
                    nan_stations = picks[picks["sta_latitude"].isnull()]
                    nan_stations = nan_stations[["network", "station"]].drop_duplicates()
                    # nan_stations.reset_index(drop=True, inplace=True)
                    
                    
                    warnings.warn("Some stations do not have coordinates. Activate debug mode in Events.get_picks to display them.")
                    if debug:
                        print("Stations with missing coordinates:")
                        print(nan_stations)

                # Compute distances, azimuths, and back-azimuths between event and station locations
                picks = get_distance_in_dataframe(
                    data=picks,
                    lat1_name="src_latitude",
                    lon1_name="src_longitude",
                    lat2_name="sta_latitude",
                    lon2_name="sta_longitude",
                    columns=["utdq_distance", "utdq_azimuth", "utdq_bazimuth"]
                )

                # Compute travel time by subtracting event origin time from pick time
                picks["utdq_time"] = picks["time"] - picks["src_origin_time"]
                picks["utdq_time"] = picks["utdq_time"].apply(lambda x: x.total_seconds())

            else:
                raise Exception("stations must be an instance of Stations")

        # print(picks[['ev_id','src_latitude','src_longitude','src_depth',
        #              'src_origin_time','network','station','sta_latitude',
        #              'sta_longitude','sta_elevation','utdq_distance',
        #              'utdq_azimuth','utdq_bazimuth','utdq_time']])
        # print(picks.info())
        
        picks["utdq_real"] = True

        picks.drop_duplicates(subset=["ev_id", "network", "station", "phase_hint","time"],
                              ignore_index=False, inplace=True)
                            #   ignore_index=True, inplace=True)

        # Define additional columns to keep in the final DataFrame
        add_columns = ["utdq_real","utdq_distance", "utdq_azimuth", "utdq_bazimuth", "utdq_time"]
        
        if stations is not None:
            # Select relevant columns for the final output
            picks = picks[out_columns + add_columns]
        else:
            picks = picks[out_columns]
            

        return Picks(data=picks, author=author)

    