from utdquake.bank.bank import EventBank
from obspy import read_inventory

path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/JAPAN"
stations_path = "/groups/igonin/ecastillo/Bank/stations/JAPAN.xml"

stations = read_inventory(stations_path)
stations_df = stations.to_df()

ebank = EventBank(
        bank_path=path,
        path_structure='{year}/{month}/{day}/{hour}',
        name_structure='{event_id_end}',
        format='quakeml'
    )

# print(ebank.read_index().sort_values("time"))

ebank.append_stations(
                    stations=stations_df,
                    starttime="2023-03-01T00:00:00",
                    endtime="2023-03-09T16:00:00",
                    chunk_seconds=7200)