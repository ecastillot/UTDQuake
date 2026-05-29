.. UTDQuake documentation master file, created by
   sphinx-quickstart on Fri Jan 30 13:39:44 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. raw:: html

   <h1>Welcome to <span style="background:#E87500; color:white; padding:2px 6px; border-radius:6px;">UTD</span>Quake</h1>

.. image:: https://img.shields.io/badge/HuggingFace-Dataset-yellow?style=for-the-badge&logo=huggingface&logoColor=black
   :target: https://huggingface.co/datasets/ecastillot/UTDQuake
   :alt: Hugging Face Dataset
.. image:: https://img.shields.io/badge/GitHub-UTDQuake-black?style=for-the-badge&logo=github
   :target: https://github.com/ecastillot/UTDQuake
   :alt: GitHub Repository

.. raw:: html

   <br><br>

**University of Texas at Dallas Earthquake Dataset**

A global earthquake dataset constructed from high-quality source and receiver metadata, including associated seismic phase picks across diverse station geometries.

.. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/main/figures/utdquake_overview.png
   :width: 800px

See :ref:`dataset-section` section for details on how to access network data, events, stations, and picks. Next table shows the network data:

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/0_networks/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

Why this dataset matters?
--------------------------

Curated datasets of earthquake events and phase picks are essential for modern seismology, especially in the AI era. While waveform datasets have advanced earthquake detection, multistation picks provide complementary information crucial for phase association and earthquake location.

This dataset offers structured event catalogs, station metadata, and phase picks across networks, supporting reproducible research and the development of data-driven seismological methods.


Access the Dataset
--------------------------

Hugging Face Dataset
^^^^^^^^^^^^^^^^^^^^^

The complete UTDQuake dataset is publicly available on Hugging Face, where it can be easily explored and downloaded:

.. image:: https://img.shields.io/badge/HuggingFace-Dataset-yellow?style=for-the-badge&logo=huggingface&logoColor=black
   :target: https://huggingface.co/datasets/ecastillot/UTDQuake
   :alt: Hugging Face Dataset


GitHub Repository
^^^^^^^^^^^^^^^^^^^^^

The source code, documentation, and additional resources are hosted on GitHub:

.. image:: https://img.shields.io/badge/GitHub-UTDQuake-black?style=for-the-badge&logo=github
   :target: https://github.com/ecastillot/UTDQuake
   :alt: GitHub Repository


Installation & Usage
^^^^^^^^^^^^^^^^^^^^^^

- To install the ``UTDQuake`` Python library and begin working with the dataset programmatically, follow the instructions in the :ref:`installation-section`.

- A step-by-step quickstart guide, including examples for accessing, analyzing, and visualizing the data, can be found in the :ref:`quickstart-section`.

- For complete technical details about all available modules, classes, and functions, see the :ref:`api-section`.



Quick Overview
--------------------------

The following animation summarizes the overview figure for some of all available networks. **All figures and analyses are available** in the :ref:`overview-section` section.

.. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/main/figures/all_networks_overview.gif
   :width: 700px
   :align: center

We offer different type of figures for each network to help users better understand the data. 

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

**All figures and analyses are available** in the :ref:`overview-section` section.

Content
--------------------------

.. toctree::
   :maxdepth: 2
   
   home
   installation
   dataset
   overview
   quickstart
   api/index
   authors
   contribution
