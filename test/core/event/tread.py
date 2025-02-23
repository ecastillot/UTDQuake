# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-02-22 13:40:48
#  * @modify date 2025-02-22 13:40:48
#  * @desc [description]
#  */

from utdquake.core.event.catalog import read_catalog

picks_path = "/home/emmanuel/ecastillo/dev/utdquake/examples/custom_events/picks.db"
stations_path = "/home/emmanuel/ecastillo/dev/utdquake/examples/custom_events/stations.csv"
events_path = "/home/emmanuel/ecastillo/dev/utdquake/examples/custom_events/origin.csv"
xy_epsg = "EPSG:3116"

catalog = read_catalog(events_path,xy_epsg,stations_path=stations_path)
print(catalog)
picks = catalog.get_picks(picks_path=picks_path,author="manual")
print(picks)
