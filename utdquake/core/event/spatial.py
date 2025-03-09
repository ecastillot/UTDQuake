# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-01-24 13:56:16
#  * @modify date 2025-01-24 13:56:16
#  * @desc [description]
#  */
import pandas as pd
from operator import add
import datetime as dt
from obspy.geodetics.base import gps2dist_azimuth

from .data import DataFrameHelper
from . import utils as ut


class SinglePoint:
    """
    Represents a single geographic point with latitude, longitude, and depth.
    """

    def __init__(
        self, latitude: float, longitude: float, depth: float,
        xy_epsg: str, origin_time: dt.datetime = None
    ) -> None:
        """
        Initialize a SinglePoint instance.

        Parameters:
        - latitude (float): Latitude of the point.
        - longitude (float): Longitude of the point.
        - depth (float): Depth of the point.
        - xy_epsg (str): EPSG code for coordinate reference system.
        - origin_time (dt.datetime, optional): Origin time of the point.
        """
        self.latitude = latitude
        self.longitude = longitude
        self.depth = depth
        self.origin_time = origin_time
        self.lonlat_epsg = "EPSG:4326"
        self.xy_epsg = xy_epsg

        # Convert latitude and longitude to x and y coordinates in kilometers
        y, x = ut.single_latlon2yx_in_km(self.latitude, self.longitude, xy_epsg=xy_epsg)

        self.x = x
        self.y = y
        self.z = depth

    def __str__(self) -> str:
        """Return a string representation of the SinglePoint instance."""
        msg1 = f"Point [{self.longitude}, {self.latitude}, {self.depth}, {self.origin_time}]"
        msg2 = f"       ({self.xy_epsg}:km) -> [{self.x}, {self.y}, {self.z}, {self.origin_time}]"
        return msg1 + "\n" + msg2


class Points(DataFrameHelper):
    """
    A class to handle a collection of geographic points using a pandas DataFrame.
    """

    def __init__(self, data, xy_epsg, author, mandatory_columns=None, **kwargs) -> None:
        """
        Initialize the Points instance.

        Parameters:
        - data (pd.DataFrame): Input DataFrame containing point data.
        - xy_epsg (str): EPSG code for coordinate reference system.
        - author (str): Author/source of the data.
        - mandatory_columns (list, optional): List of required columns. Defaults to ['latitude', 'longitude'].
        """
        col_id = None
        cols = ["ev_id", "sta_id"]
        for key_id in cols:
            if key_id in data.columns.to_list():
                col_id = key_id
                break

        if col_id is None:
            raise ValueError(f"None of these columns were found: {cols}")
        self.key_id = col_id

        if mandatory_columns is None:
            mandatory_columns = ["latitude", "longitude"]

        self.lonlat_epsg = "EPSG:4326"
        self.xy_epsg = xy_epsg
        data = ut.latlon2yx_in_km(data, xy_epsg)
        super().__init__(data=data, required_columns=mandatory_columns, author=author, **kwargs)

    def get_region(self, padding=None):
        """
        Get the bounding region based on coordinate limits.

        Parameters:
        - padding (list or float, optional):
            - If list: Padding for each side [west, east, south, north] in degrees.
            - If float/int: Percentage-based padding (0 to 1) of the region size.
        """
        padding = padding or []
        lonw, lone = self.data.longitude.min(), self.data.longitude.max()
        lats, latn = self.data.latitude.min(), self.data.latitude.max()
        region = [lonw, lone, lats, latn]
        region = [round(x, 2) for x in region]

        if isinstance(padding, list):
            if len(padding) != 4:
                raise ValueError("Padding parameter must be a 4-element list")
            padding = [-padding[0], padding[1], -padding[2], padding[3]]
            region = list(map(add, region, padding))
        elif isinstance(padding, (float, int)):
            lon_distance = abs(region[1] - region[0])
            lat_distance = abs(region[3] - region[2])
            adding4lon = lon_distance * padding
            adding4lat = lat_distance * padding
            padding = [-adding4lon, adding4lon, -adding4lat, adding4lat]
            region = list(map(add, region, padding))
        return region

    def __str__(self, extended=False) -> str:
        """Return a string representation of the Points instance."""
        msg = f"Points | {self.__len__()} items"
        if extended:
            region = [round(x, 2) for x in self.get_region()]
            msg += f"\n\tregion: {region}"
        return msg

    def sort_data_by_source(self, source: SinglePoint, ascending: bool = False):
        """
        Sorts data by distance from a specified source location.

        Parameters:
        - source (SinglePoint): Reference location.
        - ascending (bool, optional): Whether to sort in ascending order. Defaults to False.
        
        Returns:
        - pd.DataFrame: Data sorted by distance from the source.
        """
        if self.data.empty:
            raise ValueError("Cannot sort an empty DataFrame")

        self.data["sort_by_r"] = self.data.apply(
            lambda row: gps2dist_azimuth(row.latitude, row.longitude,
                                         source.latitude, source.longitude)[0] / 1e3, axis=1
        )
        return self.data.sort_values("sort_by_r", ascending=ascending, ignore_index=True)

    def filter_general_region(self, polygon):
        """
        Filter points inside a specified polygon.

        Parameters:
        - polygon (list of tuples): List of (lon, lat) defining the polygon boundary.
        """
        if polygon[0] != polygon[-1]:
            raise ValueError("The first and last point in the polygon must be the same.")
        mask = self.data.apply(lambda x: ut.inside_the_polygon((x.longitude, x.latitude), polygon), axis=1)
        self.data = self.data[mask]
        return self

    def filter_rectangular_region(self, region_lims):
        """
        Filter points within a rectangular region.

        Parameters:
        - region_lims (list): [lon_min, lon_max, lat_min, lat_max].
        """
        polygon = [
            (region_lims[0], region_lims[2]),
            (region_lims[0], region_lims[3]),
            (region_lims[1], region_lims[3]),
            (region_lims[1], region_lims[2]),
            (region_lims[0], region_lims[2])
        ]
        return self.filter_general_region(polygon)

    def filter_by_r_az(self, latitude, longitude, r, az=None):
        """
        Filter data points based on distance (r) and optionally azimuth (az).

        Parameters:
        ----------
        latitude : float
            Latitude of the reference point.
        longitude : float
            Longitude of the reference point.
        r : float
            Maximum distance in kilometers to filter data points.
        az : float, optional
            Maximum azimuth in degrees to filter data points (default is None).
        
        Returns:
        -------
        self : object
            The object with updated data after filtering.
        """
        if self.empty:
            return self
        
        # Calculate distance, azimuth, and back-azimuth from the reference point
        # to each data point (latitude, longitude).
        is_in_polygon = lambda x: gps2dist_azimuth(
            latitude, longitude, x.latitude, x.longitude
        )
        data = self.data.copy()
        # data.reset_index(drop=True,inplace=True)
        
        # Apply the 'is_in_polygon' function to each row in the DataFrame.
        # This results in a Series of tuples (r, az, baz) for each data point.
        mask = data[["longitude", "latitude"]].apply(is_in_polygon, axis=1)
        
        # Convert the Series of tuples into a DataFrame with columns 'r' (distance), 
        # 'az' (azimuth), and 'baz' (back-azimuth).
        mask = pd.DataFrame(mask.tolist(), columns=["r", "az", "baz"])
        
        # Convert distance 'r' from meters to kilometers.
        mask.loc[:, "r"] /= 1e3
        
        
        data[mask.columns.to_list()] = mask
        
        data = data[data["r"] < r]
        
        if az is not None:
            data = data[data["az"] < az]
        
        self.data = data
        # print(len(data))
        # self.data.reset_index(drop=True,inplace=True)
        
        # Return the updated object to allow method chaining.
        return self

    def get_minmax_coords(self, padding=None):
        """Return the bounding coordinates with optional padding."""
        padding = padding or [5, 5, 1]
        return ut.get_minmax_coords_from_points(self.data, self.xy_epsg, padding)
