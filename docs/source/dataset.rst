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


.. _dataset-naming-subsection:
Naming: ``utdq_net``, ``network`` and ``catalog``
--------------------------------------------------

Three names identify where the data come from. They are used the same way in every table:

- ``utdq_net``: the **UTDQuake network**, i.e. the monitoring network or project that reported the
  events and picks (e.g. ``tx``, ``AEIC``, ``R05``). It is the key of the ``Network`` table and of
  every file (``events/utdq_net=tx.parquet``), and it links the four tables. Networks downloaded from
  an agency keep the agency's code (``tx``, ``AEIC``); catalogs built by research projects get an
  ``R`` code (``R01``, ``R02``, ...).
- ``catalog``: the catalog or bulletin the events of a UTDQuake network come from (e.g. ``ComCat``,
  ``ISC Bulletin``, ``ToC2ME``). Only in the ``Network`` table.
- ``network``: the `FDSN network code <https://www.fdsn.org/networks/>`_ of the station that recorded
  a pick (e.g. ``AK``), as in the pick's ``seed_id``. Only in the ``Stations`` and ``Picks`` tables. A
  UTDQuake network usually uses stations of several FDSN networks: the ``networks`` column of the
  ``Network`` table lists them.

The tables join on these keys:

.. code-block:: text

   Network  --utdq_net-->  Events  --(utdq_net, event_id)-->  Picks  --(utdq_net, network, station)-->  Stations

A station seen by two UTDQuake networks has one row in each of them, because its calculated
location is estimated from each network's own events. The distinct physical stations are the
distinct ``(network, station)`` pairs.

.. note::

   ISC reports many picks with the placeholder network code ``IR`` (its International Registry of
   stations) instead of the station's FDSN code. ISC has no FDSN station service, so UTDQuake resolves
   these stations with the `ISC station registry <http://www.isc.ac.uk/registries/>`_, matching the
   station code and the time span of its picks:

   - the station gets its **confirmed location** from the registry;
   - when exactly one FDSN network has a station with the same code at the site (within 10 km), the
     station and its picks get that **network** (``network_source = isc_registry``) and are merged with
     that network's station row if there is one (``ir_merged``);
   - a station the registry knows only as ``IR`` keeps ``network = IR``, now located
     (``network_source = isc_registry_ir``);
   - stations with two or more candidate networks, or not in the registry, keep ``IR``
     (``network_source = unresolved_ir``).

   Before the registry, an ``IR`` station was matched only to a same-code station of the same UTDQuake
   network within 10 km (``network_source = resolved_twin``). The ``seed_id`` of a pick is always the
   one reported. A dated copy of the registry and the decision of every station are kept with the
   dataset (``.utdquake/isc_registry/``), so an extension reuses them.

.. _dataset-phase-counts-subsection:
Phase counts
------------

The ``phase`` column of the ``Picks`` table keeps the label reported by the catalog (``P``, ``Pg``,
``Pn``, ``S``, ``Sg``, ``Sn``). The ``Events`` and ``Network`` tables count the picks two ways:

- per label: ``p_count``, ``pg_count``, ``pn_count``, ``s_count``, ``sg_count``, ``sn_count``;
- per phase family: ``p_arrivals`` (every P-type pick: P + Pg + Pn + any other label starting with
  ``P``) and ``s_arrivals`` (every S-type pick).

The ``p_phase_count`` and ``s_phase_count`` columns of the ``Events`` table come from ObsPlus and only
count arrivals labelled exactly ``P`` or ``S``: for catalogs that label their picks ``Pg``/``Pn``/``Sg``/``Sn``
they are close to zero. Use ``p_arrivals`` and ``s_arrivals`` instead.

.. _dataset-seismic-subsection:
Seismic Data
--------------

Seismic data is organized in four main types of data: ``Networks``, ``Stations``, ``Events``, and ``Picks`` tables. 
It also integrates `EventBanks <https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html>`_ to enable efficient access, filtering, and management of raw earthquake catalogs.

.. code-block:: text

   Directory    Format       Description
   ----------   -----------  -------------------------------------------------------
   network/     *.parquet    Network metadata (one row per utdq_net).
   events/      *.parquet    Earthquake event catalogs, one file per utdq_net.
   stations/    *.parquet    Station metadata, one file per utdq_net.
   picks/       *.parquet    Seismic phase picks, one file per utdq_net.
   banks/       *.zip        ObsPlus EventBank datasets, one per utdq_net. Can be
                             read directly using ObsPlus EventBank
                             <https://niosh-mining.github.io/obsplus/versions/latest/api/obsplus.bank.eventbank.html>.

Each dataset is organized per network and can be explored interactively using the Hugging Face dataset viewers below.

Network
^^^^^^^

The **Network** dataset contains metadata about each UTDQuake network (one row per ``utdq_net``).

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
   * - utdq_net
     - string
     - UTDQuake network code (key of every table)
   * - catalog
     - string
     - Catalog or bulletin the events come from (e.g. ``ComCat``, ``ISC Bulletin``, ``ToC2ME``)
   * - catalog_type
     - string
     - ``agency`` (bulletin of a monitoring agency), ``research`` (catalog of a research project) or ``synthetic``
   * - networks
     - string
     - FDSN network codes of the stations that recorded the picks, comma-separated, most picks first
   * - dataset_version
     - string
     - UTDQuake version that first added the network (``v1``, ``v2``); later versions may add events to it, see :ref:`versions-section`
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
     - Rows of the network's Stations table (distinct ``(network, station)`` pairs)
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
     - Original number of P-type arrivals (P, Pg, Pn, ...), before QC
   * - original_s_arrivals
     - int64
     - Original number of S-type arrivals (S, Sg, Sn, ...), before QC
   * - events
     - int64
     - Number of events after QC
   * - p_arrivals
     - int64
     - Number of P-type picks after QC (P, Pg, Pn and any other P-type label)
   * - s_arrivals
     - int64
     - Number of S-type picks after QC (S, Sg, Sn and any other S-type label)
   * - p_count, pg_count, pn_count
     - int64
     - Number of picks labelled exactly P, Pg and Pn after QC
   * - s_count, sg_count, sn_count
     - int64
     - Number of picks labelled exactly S, Sg and Sn after QC
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
   * - last_published
     - timestamp[us]
     - When this network's row was last published to the Hub
   * - uploaded_by_github
     - string
     - GitHub profile URL of the person who contributed this network
   * - contact_email
     - string
     - Contact email for the uploader
   * - doi
     - string
     - DOI of a paper this dataset is tied to, if any

.. raw:: html

   </div>

Stations
^^^^^^^

The **Stations** dataset contains metadata for each station that recorded the picks of a UTDQuake
network: one row per ``(utdq_net, network, station)``.

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
   * - utdq_net
     - string
     - UTDQuake network code
   * - network
     - string
     - FDSN network code of the station (``IR`` if unresolved, see :ref:`dataset-naming-subsection`)
   * - station
     - string
     - Station identifier
   * - channel
     - string
     - Channel identifier (Only applies for DAS data)
   * - network_type
     - string
     - ``surface`` or ``DAS``
   * - available
     - bool
     - Whether the station has a location (confirmed or calculated). False for stations that only appear in the picks
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
   * - network_source
     - string
     - Where ``network`` comes from: ``reported`` (code reported with the picks), ``isc_registry``,
       ``isc_registry_ir`` or ``unresolved_ir`` (see the ``IR`` note in :ref:`dataset-naming-subsection`)
   * - ir_merged
     - bool
     - Whether an ``IR`` station row was merged into this one
   * - db_path
     - string
     - Path to station database file

.. raw:: html

   </div>

.. note::

   Join picks to stations on ``(utdq_net, network, station)``, never on ``station`` alone: the same
   station code is used by different FDSN networks (e.g. ``AV.SPU`` in Alaska and ``UU.SPU`` in Utah,
   ~3,500 km apart). Every pick has a station row.

Events
^^^^^^^

The **Events** dataset contains the earthquakes of each UTDQuake network.

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
   * - utdq_net
     - string
     - UTDQuake network code
   * - dataset_version
     - string
     - UTDQuake version that added the event (``v1``, ``v2``, ...), see :ref:`versions-section`
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
     - Event depth, in meters below sea level, positive down (QuakeML Origin.depth convention)
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
     - Number of arrivals labelled exactly ``P`` in the preferred origin (ObsPlus; Pg and Pn are not counted, see ``p_arrivals``)
   * - s_phase_count
     - float64
     - Number of arrivals labelled exactly ``S`` in the preferred origin (ObsPlus; Sg and Sn are not counted, see ``s_arrivals``)
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
     - ``NET.STA`` codes of the stations that picked the event, comma-separated
   * - p_count, pg_count, pn_count
     - int64
     - Picks of the event labelled exactly P, Pg and Pn (picks table)
   * - s_count, sg_count, sn_count
     - int64
     - Picks of the event labelled exactly S, Sg and Sn (picks table)
   * - p_arrivals
     - int64
     - P-type picks of the event (P, Pg, Pn and any other P-type label)
   * - s_arrivals
     - int64
     - S-type picks of the event (S, Sg, Sn and any other S-type label)
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
   * - utdq_net
     - string
     - UTDQuake network code
   * - dataset_version
     - string
     - UTDQuake version that added the pick's event, see :ref:`versions-section`
   * - network
     - string
     - FDSN network code of the station (from ``seed_id``; for ``IR`` picks, resolved where possible, see :ref:`dataset-naming-subsection`)
   * - station
     - string
     - Station identifier
   * - location
     - string
     - Station location code
   * - channel
     - string
     - Seismic channel code
   * - network_source
     - string
     - Where ``network`` comes from: ``reported``, ``resolved_twin``, ``isc_registry``,
       ``isc_registry_ir`` or ``unresolved_ir`` (see the ``IR`` note in :ref:`dataset-naming-subsection`)
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
     - FDSN network code as reported with the pick (first field of ``seed_id``, e.g. ``TX``); ``network`` is the resolved code to join with
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
   network_DAS/     *.parquet    Network metadata (one row per utdq_net).
   events_DAS/      *.parquet    Earthquake event catalogs, one file per utdq_net.
   stations_DAS/    *.parquet    Metadata for DAS virtual sensors associated with each cable system in the network. (See ``channel`` column for unique sensor identifiers.)
   picks_DAS/       *.parquet    Seismic phase picks, one file per utdq_net.
   banks_DAS/       *.zip        ObsPlus EventBank datasets, one per utdq_net. Can be
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
