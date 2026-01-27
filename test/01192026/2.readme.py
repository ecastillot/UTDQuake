
from obspy import UTCDateTime
import utdquake as utdq

# loads tx
bank =  utdq.load_network("tx")   
print(bank.stats)

# read events information
df = bank.read_index()    
print(df.head())

ev_ids = df["event_id"].tolist()[:5]
picks = bank.get_picks(event_ids=ev_ids)

# get Obspy Catalog
catalog = bank.get_events(starttime=UTCDateTime("2025-07-31T00:00:00"), 
                            endtime=UTCDateTime("2025-07-31T12:00:00"))
print(catalog)
print(catalog.to_df())

# get Obspy Event
event = catalog[0]
picks = event.picks_to_df()
arrivals = event.arrivals_to_df()
print(event,picks,arrivals)


bank.save_picks()
picks = bank.load_picks()
print(picks)

bank.plot_overview("./overview.png")
bank.plot_uncertainty_boxplots("./uncertainty_boxplots.png")
bank.plot_station_location_uncertainty("./station_location_uncertainty.png")
bank.plot_stats("./stats.png")
bank.plot_pick_histograms("./histograms.png")
bank.plot_pick_stats("./pick_stats.png")
