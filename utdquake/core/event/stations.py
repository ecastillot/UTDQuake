# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-01-24 13:56:16
#  * @modify date 2025-01-24 13:56:16
#  * @desc [description]
#  */

from .spatial  import Points

class Stations(Points):
    """
    A class representing seismic stations with additional attributes.
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the Stations instance.

        Parameters:
        - *args: Positional arguments passed to the parent class.
        - **kwargs: Keyword arguments passed to the parent class.
        """
        mandatory_columns = ['sta_id', 'network', 'station', 
                             'latitude', 'longitude', 'elevation']
        super().__init__(*args, mandatory_columns=mandatory_columns, **kwargs)
        
        # Convert elevation to depth in kilometers (negative value)
        self.data["z[km]"] = self.data["elevation"] / 1e3 * -1

    def __str__(self, extended=False) -> str:
        """Return a string representation of the Stations instance."""
        msg = f"Stations | {self.__len__()} stations"
        if extended:
            region = [round(x, 2) for x in self.get_region()]
            msg += f"\n\tregion: {region}"
        return msg
    
    
    