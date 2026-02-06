.. _quickstart-section:
Quickstart
============

This guide provides a **basic overview of UTDQuake** and demonstrates how to access datasets, networks, events, and visualizations.

You can follow this guide interactively in Colab:

.. raw:: html

   <a href="https://colab.research.google.com/github/ecastillot/UTDQuake/blob/main/examples/UTDQuake_Access.ipynb" target="_blank">
      <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/>
   </a>

Access
^^^^^^^

To get started, import the package and load the dataset using the :class:`utdquake.Dataset` class:

.. code-block:: python

   import utdquake as utdq

   # dataset overview 
   dataset = utdq.Dataset()
   print(dataset)

   # network level
   network_data = dataset.networks
   print(network_data)

In addition to network-level access, the dataset allows you to retrieve aggregated information across multiple networks. You can directly access events, stations, and picks using the following methods:

- :func:`utdquake.Dataset.get_events` – retrieve event information across networks  
- :func:`utdquake.Dataset.get_stations` – retrieve station metadata  
- :func:`utdquake.Dataset.get_picks` – retrieve seismic phase picks  

Network Data
^^^^^^^

Detailed information for a specific seismic network can be accessed through the :class:`utdquake.Network` class:

.. code-block:: python

   # load network 
   network = dataset.get_network(name="tx")
   print(network)

   # events
   events = network.events
   print(events)

   # stations
   stations = network.stations
   print(stations)

   # picks
   picks = network.picks
   print(picks)

Event Bank
^^^^^^^
UTDQuake integrates an **event bank**. Check `ObsPlus EventBank <https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html>`_ for more details.

.. code-block:: python

   # get event bank
   ebank = network.bank # 

   # Example: Filter by event_id
   ev_ids = events["event_id"].iloc[:5].tolist()
   cat = ebank.get_events(event_id=ev_ids)
   print(cat)

   # Example 2: Other filter (check obsplus.EventBank for more details)
   cat2 = ebank.get_events(minmagnitude=4.3)
   print(cat2)

Visualization (Plots)
^^^^^^^

UTDQuake provides convenient plotting functions for quick data exploration. 
Check the :func:`utdquake.Network` plotting functions for more details and examples.
Or also check the :func:`utdquake.utils.plot` module for more flexibility to create your own custom plots.

.. code-block:: python

   import utdquake as utdq

   dataset = utdq.Dataset()
   dataset.plot_overview(savepath="utdquake.png")

   network = dataset.get_network(name="tx")
   network.plot_overview(savepath="overview.png")
   network.plot_uncertainty_boxplots(savepath="uncertainty_boxplots.png")
   network.plot_station_location_uncertainty(savepath="station_location_uncertainty.png")
   network.plot_stats(savepath="stats.png")
   network.plot_pick_histograms(savepath="histograms.png")
   network.plot_pick_stats(savepath="pick_stats.png")
   
.. note::

   We need `Cartopy <https://cartopy.readthedocs.io/stable/>`_ to be able to plot most of the figures.


Further Reading
^^^^^^^

- Explore all dataset methods:  :class:`utdquake.Dataset`
- Explore all network methods: :class:`utdquake.Network`  
- Check the `ObsPlus EventBank <https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html>`_ documentation for advanced event filtering.