from utdquake.download.utils import get_stations_summary

ev_path = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/events/.index.db"
stations_folder = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test/events/.stations"

summaries = get_stations_summary(ev_path, stations_folder)
print()
print(summaries.info())
print(summaries)