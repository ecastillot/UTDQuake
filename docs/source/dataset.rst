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

.. raw:: html

   <div style="overflow-x:auto; max-width:100%;">

.. list-table:: Structure of the Networks table in UTDQuake.
   :header-rows: 1
   :class: scroll-table
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - network
     - string
     - Network identifier
   * - continent
     - string
     - Continent of network
   * - provider
     - string
     - Data provider
   * - provider_url
     - string
     - Provider URL
   * - country
     - string
     - Country
   * - agency
     - string
     - Responsible agency
   * - total_stations
     - int64
     - Total stations in network
   * - located_stations
     - int64
     - Stations with location information
   * - confirmed_stations
     - int64
     - Verified stations
   * - calculated_stations
     - int64
     - Derived stations
   * - original_events
     - int64
     - Original number of events
   * - original_p_arrivals
     - int64
     - Original number of P picks
   * - original_s_arrivals
     - int64
     - Original number of S picks
   * - events
     - int64
     - Number of events after QC
   * - p_arrivals
     - int64
     - Number of P picks after QC
   * - s_arrivals
     - int64
     - Number of S picks after QC
   * - start_time
     - timestamp[us]
     - Start of catalog
   * - end_time
     - timestamp[us]
     - End of catalog
   * - approx_lon_min
     - float64
     - Minimum longitude
   * - approx_lon_max
     - float64
     - Maximum longitude
   * - approx_lat_min
     - float64
     - Minimum latitude
   * - approx_lat_max
     - float64
     - Maximum latitude
   * - score
     - int64
     - Quality score

.. raw:: html

   </div>

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

.. raw:: html

   <div style="overflow-x:auto; max-width:100%;">

.. list-table:: Structure of the Stations table in UTDQuake.
   :header-rows: 1
   :class: scroll-table
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - network
     - string
     - Network identifier
   * - station
     - string
     - Station identifier
   * - channel
     - string
     - Channel identifier (Only applies for DAS data)
   * - available
     - bool
     - Availability of station metadata
   * - confirmed
     - bool
     - Whether station is confirmed
   * - confirmed_latitude
     - float64
     - Confirmed latitude
   * - confirmed_longitude
     - float64
     - Confirmed longitude
   * - confirmed_elevation
     - float64
     - Confirmed elevation
   * - calculated
     - bool
     - Whether station location is calculated
   * - calculated_latitude
     - float64
     - Calculated latitude
   * - calculated_longitude
     - float64
     - Calculated longitude
   * - calculated_latitude_std
     - float64
     - Standard deviation of calculated latitude
   * - calculated_longitude_std
     - float64
     - Standard deviation of calculated longitude
   * - creation_time
     - timestamp[us]
     - Time of station entry creation
   * - calculated_num_entries
     - int64
     - Number of entries used for calculation
   * - db_path
     - string
     - Path to station database file

.. raw:: html

   </div>

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

.. raw:: html

   <div style="overflow-x:auto; max-width:100%;">

.. list-table:: Structure of the Events table in UTDQuake.
   :header-rows: 1
   :class: scroll-table
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - network
     - string
     - Network identifier
   * - time
     - timestamp[ns]
     - Origin time of the event
   * - latitude
     - float64
     - Event latitude
   * - longitude
     - float64
     - Event longitude
   * - depth
     - float64
     - Event depth, in meters (QuakeML Origin.depth convention)
   * - magnitude
     - float64
     - Preferred magnitude value
   * - azimuthal_gap
     - float64
     - Azimuthal gap of station coverage
   * - event_description
     - string
     - Textual description of the event
   * - associated_phase_count
     - float64
     - Number of associated phases
   * - event_id
     - string
     - Unique event identifier
   * - horizontal_uncertainty
     - float64
     - Horizontal location uncertainty
   * - local_magnitude
     - float64
     - Local magnitude (ML)
   * - moment_magnitude
     - float64
     - Moment magnitude (Mw)
   * - duration_magnitude
     - float64
     - Duration magnitude
   * - magnitude_type
     - string
     - Type of reported magnitude
   * - p_phase_count
     - float64
     - Number of associated P phases
   * - s_phase_count
     - float64
     - Number of associated S phases
   * - p_pick_count
     - float64
     - Number of P-wave picks
   * - s_pick_count
     - float64
     - Number of S-wave picks
   * - standard_error
     - float64
     - Standard error of location/magnitude solution
   * - used_phase_count
     - float64
     - Number of phases used in location
   * - station_count
     - float64
     - Number of stations used
   * - vertical_uncertainty
     - float64
     - Depth uncertainty (vertical)
   * - updated
     - timestamp[ns]
     - Last update time of event
   * - author
     - string
     - Author of the solution
   * - agency_id
     - string
     - Contributing agency identifier
   * - creation_time
     - timestamp[ns]
     - Time when event was created in catalog
   * - version
     - string
     - Event solution version
   * - stations
     - string
     - List of stations contributing to event
   * - preferred_origin_id
     - string
     - Identifier of preferred origin solution

.. raw:: html

   </div>

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

.. raw:: html

   <div style="overflow-x:auto; max-width:100%;">

.. list-table:: Structure of the Arrivals (Picks) table in UTDQuake.
   :header-rows: 1
   :class: scroll-table
   :widths: 25 15 60

   * - Column
     - Type
     - Description
   * - network
     - string
     - Network identifier
   * - station
     - string
     - Station identifier
   * - channel
     - string
     - Seismic channel code
   * - location
     - string
     - Station location code
   * - phase
     - string
     - Phase type (e.g., P, S)
   * - time
     - timestamp[ns]
     - Pick arrival time
   * - travel_time
     - float64
     - Travel time from origin to arrival
   * - travel_time_zscore
     - float64
     - Z-score of travel time relative to expected values
   * - distance
     - float64
     - Epicentral distance
   * - linear_hyp_distance
     - float64
     - Linear hypocentral distance
   * - azimuth
     - float64
     - Azimuth from event to station
   * - evaluation_mode
     - string
     - Evaluation mode of pick (automatic/manual)
   * - event_id
     - string
     - Associated event identifier
   * - pick_agency
     - string
     - Agency that provided the pick
   * - origin_time
     - timestamp[ns]
     - Origin time of associated event
   * - resource_id
     - string
     - Unique resource identifier
   * - seed_id
     - string
     - SEED identifier (network.station.location.channel)
   * - pick_id
     - string
     - Identifier of associated pick
   * - time_correction
     - float64
     - Time correction applied to pick
   * - takeoff_angle
     - float64
     - Estimated takeoff angle at source
   * - time_residual
     - float64
     - Difference between observed and theoretical travel time
   * - horizontal_slowness_residual
     - float64
     - Residual of horizontal slowness
   * - backazimuth_residual
     - float64
     - Residual of backazimuth
   * - time_weight
     - float64
     - Weight assigned to arrival time
   * - horizontal_slowness_weight
     - float64
     - Weight of horizontal slowness constraint
   * - backazimuth_weight
     - float64
     - Weight of backazimuth constraint
   * - earth_model_id
     - string
     - Velocity/earth model used
   * - creation_time
     - timestamp[ns]
     - Time arrival was created
   * - author
     - string
     - Author of arrival solution
   * - agency_id
     - string
     - Contributing agency identifier
   * - origin_id
     - string
     - Associated origin identifier
   * - preferred_origin_id
     - string
     - Preferred origin for this arrival

.. raw:: html

   </div>

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
