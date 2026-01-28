from utdquake.fdsn.client import Client
from utdquake.fdsn.events import download_events
from utdquake.fdsn.config import (DownloadConfig,
    CatalogConfig, StationConfig, PerformanceConfig)
from obspy import UTCDateTime
import logging

logging.basicConfig(level=logging.INFO)

tx = "USGS"
client = Client(tx)
starttime = UTCDateTime("2020-01-27T00:00:00")
endtime = UTCDateTime("2020-01-27T04:00:00")

event_path = "/groups/igonin/ecastillo/utdquake/test/01272026_v/test"


config = DownloadConfig(
    catalog=CatalogConfig(
                        starttime=starttime,
                        endtime=endtime,
                    ),
    stations=StationConfig(
                        compute_distance=True,
                    ),
    performance=PerformanceConfig(
                        chunk_size=1000,
                    ),
)

downloaded_events = download_events(client,
                                    events_bank_path=event_path,
                                    config=config)


