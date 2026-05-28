.. _dataset-section:
Dataset
============================

UTDQuake is a global earthquake dataset that provides multi-station :ref:`dataset-seismic-subsection` and :ref:`dataset-DAS-subsection` in a unified tabular framework. 


UTDQuake enables reproducible research and facilitates the development and benchmarking of 
pick-based methods for phase association and earthquake location.

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


.. _dataset-seismic-subsection:
Seismic Data
--------------

Seismic data is organized in four main types of data: ``Networks``, ``Stations``, ``Events``, and ``Picks`` tables. 
It also integrates `EventBanks <https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html>`_ to enable efficient access, filtering, and management of raw earthquake catalogs.

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

.. _dataset-das-subsection:
DAS Data
--------------

To maintain consistency with the overall UTDQuake architecture, DAS data are organized using the same tabular structure as seismic data, including ``Networks``, ``Stations``, ``Events``, and ``Picks`` tables. In this representation, each DAS channel is treated as an individual station.

Accordingly, an additional column, ``channel``, is included in the ``Stations`` table to uniquely identify each sensing position along the fiber, while the ``station`` field denotes the corresponding cable system.

This design preserves compatibility with conventional seismic metadata structures while enabling representation of the extremely dense spatial sampling characteristic of DAS arrays.

.. code-block:: text

   Directory    Format       Description
   ----------   -----------  -------------------------------------------------------
   networks_DAS/    *.parquet    Network metadata.
   events_DAS/      *.parquet    Earthquake event catalogs per network.
   stations_DAS/    *.parquet    Metadata for DAS virtual sensors associated with each cable system in the network. (See ``channel`` column for unique sensor identifiers.)
   picks_DAS/       *.parquet    Seismic phase pick datasets per network.
   bank_DAS/        *.zip        ObsPlus EventBank datasets, one per Network_DAS. Can be
                             read directly using ObsPlus EventBank
                             <https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html>.

Each dataset is organized per network and can be explored interactively using the Hugging Face dataset viewers below.

Network_DAS
^^^^^^^^^^^^^^

The **Network_DAS** dataset contains metadata describing the DAS fiber-optic acquisition system and associated project information.

In this context, one ``station`` correspond to one cable system, and the ``channel`` identifies the sensing position along the fiber.

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/0_networks_DAS/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

Stations_DAS
^^^^^^^^^^^^^^

The **Stations_DAS** dataset contains metadata for DAS virtual sensors associated with each fiber-optic cable system. In this representation, each DAS channel is treated as an individual station, while the ``station`` field identifies the corresponding cable system and the ``channel`` field uniquely identifies the sensing position along the fiber.

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/1_stations_DAS/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

Events_DAS
^^^^^^^^^^^^^^

The **Events_DAS** dataset contains earthquake metadata associated with DAS recordings. Event locations and origin information were obtained from agencies rather than being directly determined from DAS observations. For each event, theoretical travel times were computed and used to associate automatic P- and S-phase picks within a 3-second time window across DAS virtual sensors.

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/2_events_DAS/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

Picks_DAS
^^^^^^^^^^^^^^

The **Picks_DAS** dataset contains seismic phase arrival picks associated with DAS virtual sensors. Each pick is linked to a specific DAS channel, enabling phase detection and timing information to be represented within the same event-pick architecture used for conventional seismic networks.

.. raw:: html

   <iframe
   src="https://huggingface.co/datasets/ecastillot/UTDQuake/embed/viewer/3_picks_DAS/metadata"
   frameborder="0"
   width="100%"
   height="560px"
   ></iframe>

.. _figures-subsection:
