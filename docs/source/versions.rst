.. _versions-section:
Release versions
================

How dataset and package versions work, and how to read a fixed version, is explained in
:ref:`installation-versions-subsection`. This page lists what each dataset version contains and changes.

The ``dataset_version`` column says which version added a row:

- ``Network`` table: the version that first added the network.
- ``Events`` and ``Picks`` tables: the version that added the event. A later version can add events to
  a network that already exists, so one network can hold events of several versions:

.. code-block:: python

   v1_events = events[events["dataset_version"] == "v1"]


v2.0 (in preparation)
---------------------

- **New UTDQuake networks.** ``CM`` (Servicio Geologico Colombiano) and the research catalogs, now with
  ``R`` codes:

  .. list-table::
     :header-rows: 1
     :widths: 15 25 60

     * - ``utdq_net``
       - Name before v1.0
       - ``catalog``
     * - ``R01``
       - ``ISOR``
       - COSEISMIQ
     * - ``R02``
       - ``SYN_QTM``
       - Synthetic Ridgecrest 2019 catalog
     * - ``R03``
       - ``tx_highres``
       - tx_highres (TexNet)
     * - ``R04``
       - ``GEYSERS``
       - The Geysers
     * - ``R05``
       - ``5B``
       - ToC2ME
     * - ``R06``
       - ``ESPOO``
       - ESPOO
     * - ``R07``
       - ``LASSO``
       - LASSO
     * - ``R08``
       - ``comcat_deep30``
       - ComCat events z>30km (events deeper than 30 km only)

- **More events.** The existing networks are extended to up to 20,000 events per network after quality
  control, backwards in time and forward to 2026. The new events are labelled ``v2``; the events of
  ``v1.0`` keep ``v1``.
- Stations of ISC networks are resolved with the ISC station registry as in ``v1.0``; the decisions of
  ``v1.0`` are reused.


v1.0
----

The dataset of the UTDQuake paper.

**Contents**

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * -
     - Seismic
     - DAS
   * - UTDQuake networks
     - 82
     - 1 (``UWF``)
   * - Earthquakes (after QC)
     - 346,487
     - 450
   * - Picks
     - 10,100,513
     - 7,816,115
   * - P-type picks (P / Pg / Pn)
     - 6,754,777 (5,064,898 / 737,603 / 952,276)
     - 2,930,110
   * - S-type picks (S / Sg / Sn)
     - 3,345,736 (2,423,759 / 645,592 / 276,385)
     - 4,886,005
   * - Stations (distinct ``network``, ``station``)
     - 17,844 (16,225 located, 15,343 confirmed)
     - 3 cables, 22,500 channels

**Changes from v0.3**

- **Naming.** ``utdq_net`` names the UTDQuake network (the key of every table and file,
  ``events/utdq_net=tx.parquet``); ``network`` is now the FDSN code of the station in the stations and
  picks tables; the network table gains ``catalog``, ``catalog_type``, ``networks`` and
  ``dataset_version``.
- **Stations.** Stations are keyed by ``(utdq_net, network, station)``, so two stations with the same code
  in different FDSN networks are no longer mixed. Stations that appear only in picks get a row. Totals
  over several networks count distinct ``(network, station)`` pairs.
- **ISC ``IR`` stations.** Stations reported by ISC with the placeholder code ``IR`` get their location
  and, when unambiguous, their FDSN network from the ISC station registry: about 12,800 stations are reassigned to their network and about
  26,000 get a confirmed location.
- **Phase counts.** ``p_arrivals``/``s_arrivals`` count every P-type and S-type pick, and new columns count
  each label (``p_count``, ``pg_count``, ...). Before, only picks labelled exactly ``P`` or ``S`` were
  counted.
- **Versions.** ``dataset_version`` on networks, events and picks.
- **Fixes.** Calculated station longitudes outside [-180, 180] are wrapped (47 stations) and averaged
  around the circle; maps of networks across the antimeridian (e.g. the Aleutians) are drawn correctly;
  a few bank files not in the bank index were removed and stale index rows dropped.
- **Networks.** The research catalogs and ``CM`` are not part of ``v1.0``; they are released, with ``R``
  codes, in ``v2.0``.


v0.3
----

The dataset as published before version 1.0 (files ``network=<name>.parquet``), read by ``utdquake``
0.3. It is kept as a tag so that earlier results can be reproduced.
