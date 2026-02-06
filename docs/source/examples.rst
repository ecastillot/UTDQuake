Examples
============

The following examples demonstrate how to interact with UTDQuake using Jupyter notebooks.
Each notebook can be opened and executed directly in Google Colab.

.. raw:: html

   <div align="center">

.. list-table:: Notebooks
   :widths: 30 30
   :header-rows: 1

   * - Notebook
     - Colab link
   
   * - Quickstart
     - .. raw:: html

         <a href="https://colab.research.google.com/github/ecastillot/UTDQuake/blob/main/examples/UTDQuake_Access.ipynb" target="_blank">
            <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/>
         </a>

.. raw:: html

   </div>

More examples coming soon!

Quickstart
----------

This guide provides a **basic overview of UTDQuake** and demonstrates how to access datasets, networks, events, and visualizations.

You can follow this guide interactively in Colab:

.. raw:: html

   <a href="https://colab.research.google.com/github/ecastillot/UTDQuake/blob/main/examples/UTDQuake_Access.ipynb" target="_blank">
      <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/>
   </a>

Access
^^^^^^^

First, import the package and load the dataset:

.. code-block:: python

   import utdquake as utdq

   # dataset overview 
   dataset = utdq.Dataset()
   print(dataset)

   # network level
   network_data = dataset.networks
   print(network_data)

Network Data
^^^^^^^

You can access detailed information about a specific network:

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

UTDQuake provides convenient plotting functions for quick data exploration:

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

   All plotting functions accept a `savepath` argument. If omitted, the plot will be shown interactively.

Further Reading
^^^^^^^

- Explore all dataset methods: `dataset.*`  
- Explore all network methods: `network.*`  
- Check the `obsplus.EventBank` documentation for advanced event filtering.