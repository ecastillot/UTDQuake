import utdquake as utdq

# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

dataset = utdq.Dataset()
print(dataset)

# network level
network_data = dataset.networks
print(network_data)

# dataset.plot_overview(savepath="utdquake.png")


# load network 
network = dataset.get_network(name="tx")
print(network)

# network.plot_overview(savepath="overview.png")
# network.plot_uncertainty_boxplots(savepath="uncertainty_boxplots.png")
# network.plot_station_location_uncertainty(savepath="station_location_uncertainty.png")
# network.plot_stats(savepath="stats.png")
# network.plot_pick_histograms(savepath="histograms.png")
# network.plot_pick_stats(savepath="pick_stats.png")

# events
events = network.events
print(events)

# stations
stations = network.stations
print(stations)

# picks
picks = network.picks
print(picks)

# get event bank
ebank = network.bank # check obsplus.EventBank for more details
ev_ids = events["event_id"].iloc[:5].tolist()
cat = ebank.get_events(event_id=ev_ids)
print(cat)
cat2 = ebank.get_events(minmagnitude=4.3)
print(cat2)
