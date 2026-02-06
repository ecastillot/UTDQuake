.. _dataset-section:
Dataset
============================

The UTDQuake dataset contains seismic data organized by network, stations, events, and picks.
It is designed for earthquake analysis, phase association, and network monitoring. Each dataset
component is described below with formats, contents, and interactive previews.

Access
-------

The dataset is available on Hugging Face:

.. image:: https://img.shields.io/badge/HuggingFace-Dataset-yellow?style=for-the-badge&logo=huggingface&logoColor=black
   :target: https://huggingface.co/datasets/ecastillot/UTDQuake
   :alt: Hugging Face Dataset

It is also hosted on GitHub:

.. image:: https://img.shields.io/badge/GitHub-UTDQuake-black?style=for-the-badge&logo=github
   :target: https://github.com/ecastillot/UTDQuake
   :alt: GitHub Repository

Structure
-------

.. code-block:: text

   Directory    Format       Description
   ----------   -----------  -------------------------------------------------------
   networks/    *.parquet    Network metadata.
   events/      *.parquet    Earthquake event catalogs per network.
   stations/    *.parquet    Station metadata per network.
   picks/       *.parquet    Seismic phase pick datasets per network.
   bank/        *.zip        ObsPlus EventBank datasets, one per network. Can be
                             read directly using ObsPlus EventBank
                             <https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html>.

Data Types
-------

The UTDQuake dataset contains four main types of data: **Network**, **Stations**, **Events**, and **Picks**.
Each dataset is organized per network and can be explored interactively using the Hugging Face dataset viewers below.

Network
^^^^^^^

The **Network** dataset contains metadata about each seismic network.

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/0_networks/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

Stations
^^^^^^^

The **Stations** dataset contains metadata for each seismic station.

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/1_stations/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

Events
^^^^^^^

The **Events** dataset contains earthquake catalogs for each network.

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/2_events/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

Picks
^^^^^^^

The **Picks** dataset contains seismic phase picks associated with each event.

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/3_picks/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

.. _figures-subsection:
