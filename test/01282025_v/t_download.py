import utdquake as utdq

dataset = utdq.Dataset()
print(dataset)

# network level
network_data = dataset.networks
print(network_data)

dataset.plot_overview(savepath="utdquake.png")


# load network 
network = dataset.get_network(name="tx")
print(network)

network.plot_overview(savepath="overview.png")
network.plot_uncertainty_boxplots(savepath="uncertainty_boxplots.png")
network.plot_station_location_uncertainty(savepath="station_location_uncertainty.png")
network.plot_stats(savepath="stats.png")
network.plot_pick_histograms(savepath="histograms.png")
network.plot_pick_stats(savepath="pick_stats.png")
exit()

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

# ebank = network.bank # check obsplus.EventBank for more details
# cat = ebank.get_events(minmagnitude=4.3)
# print(cat)


# print(dataset)
# print(dataset.description)


# from utdquake.core.data import HFDownloader, download_utdquake
# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# from utdquake.core.config import get_root, CORE_DIR

# from utdquake.core.utdquake import Network, UTDQuake

# utdq = UTDQuake()
# # print(utdq.description)
# test_fig = "/groups/igonin/ecastillo/utdquake/test/01282025_v/t.png"
# utdq.plot_utdq_overview(savepath=test_fig)
# print(utdq.networks)
# print(utdq.stations)
# print(utdq.events)
# network = utdq.get_network("tx")
# print(network)



# network = Network("uu")
# print(network)

# test_fig = "/groups/igonin/ecastillo/utdquake/test/01282025_v/t.png"
# network.plot_overview(savepath=test_fig)
# network.plot_stats(savepath=test_fig)
# network.plot_uncertainty_boxplots(savepath=test_fig)
# network.plot_pick_stats(savepath=test_fig)
# network.plot_station_location_uncertainty(savepath=test_fig)
# network.plot_pick_histograms(savepath=test_fig)


# print(network.__str__(extended=True))
# print(network.description)
# bank = network.bank()
# print(bank)
# events = network.events()
# print(events)
# picks = network.picks()
# print(picks)

# print(get_root())
# print(CORE_DIR)

# local_path = "/groups/igonin/ecastillo/test"
# download_utdquake(local_path, networks=["uu","tx"])


# downloader = HFDownloader()

# Download all networks (no filtering)
# networks = downloader.download("network")

# print(networks.to_pandas())

# # Download stations for a specific network
# stations = downloader.download("stations", network="RSNC")
# print(stations.to_pandas())

# Download events for multiple networks
# events = downloader.download("events", network=["uu", "uw"])
# print(events.to_pandas())

# Download picks in streaming mode
# picks_stream = downloader.download("picks", network="RSNC", streaming=True)
# print(picks_stream)

# picks_stream = downloader.download("picks", network="uw", streaming=False)
# print(picks_stream.to_pandas())