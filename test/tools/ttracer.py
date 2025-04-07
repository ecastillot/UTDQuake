import sys
lib = None
lib = "/home/edc240000/UTDQuake"
if lib is not None:
    sys.path.append(lib)

import pandas as pd
from obspy import UTCDateTime
from utdquake.core.event.catalog import read_catalog
from utdquake.tools.tracer import MyStream, plot_traces
from utdquake.clients.fdsn.client import Client
from matplotlib import pyplot as plt


stations_path = "/home/edc240000/UTDQuake/examples/custom_events/stations.csv"
events_path = "/home/edc240000/UTDQuake/examples/custom_events/origin.csv"
picks_path = "/home/edc240000/UTDQuake/examples/custom_events/picks.db"

stations = pd.read_csv(stations_path)

catalog = read_catalog(events_path=events_path,
                       xy_epsg="EPSG:3116",
                       stations_path=stations_path)

picks = catalog.get_picks(picks_path=picks_path,author="manual")
data = picks.data

data = data.rename(columns={"time":"arrival_time"})
print(data.info())


provider = "texnet"
client =  Client(provider)
st = client.get_waveforms(network="TX",station="PE*,PB*",
                          location="00",
                          channel="HHZ",
                           starttime=UTCDateTime("2024-04-19 00:33:28"),
                           endtime=UTCDateTime("2024-04-19 00:33:57"))
st = st.select(component="Z")


myst = MyStream(st.traces,stations)
myst.sort_from_source(source=(-103.884,31.488),invert=True)
myst.detrend().normalize()
print(st)


# Define color map for different authors and phases
color_authors = {
    "texnet": {"P": "blue", "S": "red"},
}

picks_list = {"texnet":data}

# plot_traces(myst,picks_list,color_authors)
fig,ax,legend_elements = plot_traces(myst,picks_list,color_authors)

fig.legend(handles=legend_elements, 
               loc='upper right',  
                fontsize=18,
                title_fontsize=18,
            title="Phases")

# Make the title bold
legend = fig.legends[-1]  # get the last legend added to the figure
legend.get_title().set_weight('bold')

savefig="/home/edc240000/UTDQuake/test/tools/fig_ttracer.png"
fig.savefig(savefig, dpi=300, bbox_inches='tight')
plt.show()