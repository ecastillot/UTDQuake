.. _quickstart-section:
Quickstart
============

This guide provides a **basic overview of UTDQuake** and demonstrates how to access datasets, networks, events, and visualizations.

.. warning::

   Make sure to use the latest stable version of UTDQuake.

   .. image:: https://img.shields.io/pypi/v/UTDQuake?label=pypi&cacheSeconds=300
      :target: https://pypi.org/project/UTDQuake/
      :alt: PyPI version

You can follow this guide interactively in Colab:

.. raw:: html

   <a href="https://colab.research.google.com/github/ecastillot/UTDQuake/blob/main/examples/UTDQuake_Access.ipynb" target="_blank">
      <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/>
   </a>

Dataset Overview
^^^^^^^

To get started, import the package and load the dataset using the :class:`utdquake.Dataset` class:

.. code-block:: python

   import utdquake as utdq

   # dataset overview 
   dataset = utdq.Dataset(das=False) # set das=True to load DAS data
   print(dataset)

   # network level
   network_data = dataset.networks
   display(network_data)

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
   display(network)

   # events
   events = network.events
   display(events)

   # stations
   stations = network.stations
   display(stations)

   # picks
   picks = network.picks
   display(picks)

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

Catalogs to UTDQuake
^^^^^^^
UTDQuake provides convenient functions to convert catalogs to UTDQuake format.

Apply QC
"""""""""""""

.. code-block:: python

   import utdquake as utdq # Make sure we have the package imported to access the conversion functions
   import logging # use logging to see the QC process in the console
   logging.basicConfig(level=logging.DEBUG)

   cat.apply_utdq_qc(debug=True, inplace=True) 
   print(cat)

.. list-table:: Minimum QC criteria applied to events and picks.
   :class: compact-table centered-table
   :name: event_pick_qc
   :header-rows: 1

   * - Category
     - Parameter
     - Value
   * - Event
     - Minimum associated phase count
     - 4
   * - Event
     - Minimum used phase count
     - 4
   * - Event
     - Minimum station count
     - 3
   * - Event
     - Maximum standard error
     - 1.8
   * - Pick
     - Minimum travel time
     - 0
   * - Pick
     - Minimum hypocentral distance
     - 0
   * - Pick
     - Minimum epicentral distance
     - 0
   * - Pick
     - Minimum S-P time difference (including ``Sn-Pn`` and ``Sg-Pg``)
     - > 0

Convert to UTDQuake Format
"""""""""""""

.. code-block:: python

   import utdquake as utdq # Make sure we have the package imported to access the conversion functions
   print("Events")
   display(cat.utdq_events_to_df())
   print("Picks")
   display(cat.utdq_picks_to_df())

.. list-table:: Events
   :class: compact-table centered-table
   :header-rows: 1

   * - time
     - latitude
     - longitude
     - depth
     - magnitude
     - event_id
     - ...
   * - 2025-01-14 10:18:25
     - 31.962
     - -102.990
     - 8618.2
     - 1.8
     - texnet2025aynz
     - ...
   * - 2025-01-14 12:19:34
     - 31.731
     - -104.092
     - 6574.1
     - 1.6
     - texnet2025aysb
     - ...

.. list-table:: Picks
   :class: compact-table centered-table
   :header-rows: 1

   * - network
     - station
     - phase
     - time
     - travel_time (s)
     - distance (deg)
     - ...
   * - 2T
     - EF73
     - P
     - 2025-01-30 03:26:40.660782
     - 3.782
     - 0.087
     - ...
   * - 2T
     - EF61
     - P
     - 2025-01-30 03:26:41.636254
     - 4.757
     - 0.138
     - ...
   * - TX
     - EF04
     - P
     - 2025-01-30 03:26:41.924392
     - 5.045
     - 0.159
     - ...

Travel Time Model
^^^^^^^

Each network has a travel-time model, fitted per phase from that network's own picks
(see :ref:`upload-dataset-section` if you're publishing a network and need to build one).
Once it exists, load and query it like this:

.. code-block:: python

   tt = network.travel_time
   predictions = tt.predict(phase="P", distance=[2,3,4,5,10,20,30,40,50,60]) #in km
   display(predictions)

.. list-table::
   :class: compact-table centered-table
   :header-rows: 1

   * - distance (km)
     - sigma (s)
     - p1 (s)
     - p25 (s)
     - p50 (s)
     - p75 (s)
     - p99 (s)
   * - 2
     - 0.138
     - 0.360
     - 0.578
     - 0.661
     - 0.768
     - 0.924
   * - 3
     - 0.285
     - 0.160
     - 0.694
     - 0.896
     - 1.077
     - 1.468
   * - 4
     - 0.295
     - 0.254
     - 0.888
     - 1.155
     - 1.331
     - 1.717
   * - 5
     - 0.304
     - 0.349
     - 1.083
     - 1.414
     - 1.584
     - 1.966
   * - 10
     - 0.411
     - 1.154
     - 1.907
     - 2.220
     - 2.479
     - 3.241

.. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/main/figures/travel_time_model.png
   :width: 600px
   :align: center
   :alt: UTDQuake Travel Time Model


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
   network.plot_stats(savepath="stats.png")
   network.plot_pick_histograms(savepath="histograms.png")
   network.plot_phase_count_radar_by_magnitude(savepath="phase_count_radar.png")
   network.plot_station_location_uncertainty(savepath="station_location_uncertainty.png")
   network.plot_uncertainty_boxplots(savepath="uncertainty_boxplots.png")
   network.plot_travel_time_qc(savepath="plot_travel_time_qc.png")
   network.plot_travel_time_vs_distance(savepath="travel_time_vs_distance.png")
   network.plot_travel_time_vs_distance_zscore(savepath="plot_travel_time_vs_distance_zscore.png")

.. note::

   We need `Cartopy <https://cartopy.readthedocs.io/stable/>`_ to be able to plot figures with maps.


Available Figures 
"""""""""""""""""

The table below summarizes the main categories of figures generated by UTDQuake.
These plots are designed to help users quickly evaluate data quality, spatial coverage, and picking performance.

.. raw:: html

   <div align="center">

.. list-table:: UTDQuake analysis
   :widths: 30 30 30
   :header-rows: 1

   * - Overview
     - Stats
     - P & S Picks Analysis

   * - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_overview.png
          :width: 200px
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_stats.png
          :width: 200px
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_pick_histograms.png
          :width: 200px

   * - **Magnitude & Phases Analysis**
     - **Uncertainty in station location**
     - **Uncertainty in EQ location**
       
   * - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_phase_count_radar.png
          :width: 200px
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_station_location_uncertainty.png
          :width: 200px
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_uncertainty_boxplots.png
          :width: 200px
     

   * - **General Travel Time Overview**
     - **Travel Time**
     - **Travel Time Zscore**
         
   * - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_travel_time_qc.png
          :width: 200px
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_travel_time_vs_distance.png
          :width: 200px
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_travel_time_vs_distance_P_zscore.png
          :width: 200px

.. raw:: html

   </div>

Further Reading
^^^^^^^

- Explore all dataset methods:  :class:`utdquake.Dataset`
- Explore all network methods: :class:`utdquake.Network`
- Check the `ObsPlus EventBank <https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html>`_ documentation for advanced event filtering.
- Have your own catalog (QuakeML or an ObsPy ``Catalog``) and want it in UTDQuake? See :ref:`upload-dataset-section`.