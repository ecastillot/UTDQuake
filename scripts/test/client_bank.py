import obsplus
from obspy.clients.fdsn import Client
from obsplus.interfaces import EventClient



path = "/home/edc240000/scratch/utdbank"
ebank = obsplus.EventBank(base_path=path,
                          path_structure='{year}/{month}/{day}/{hour}',
                          name_structure='{event_id_end}',
                          format='quakeml')

provider = "http://coseismiq.ethz.ch:8080"
client = Client(provider)
# ev_client = EventClient(client)
# print(ev_client)

ebank.put_events(client)
