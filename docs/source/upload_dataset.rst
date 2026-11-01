.. _upload-dataset-section:
Upload your dataset
============================

Turn your catalog (an ObsPy :class:`~obspy.core.event.Catalog` or a folder of QuakeML files with picks)
into a UTDQuake network on the
`Hugging Face dataset <https://huggingface.co/datasets/ecastillot/UTDQuake>`_.

.. list-table::
   :widths: 8 32 60
   :header-rows: 1

   * - Step
     - Function
     - What it does
   * - 1
     - ``ebank.put_events``
     - load your events into an event bank
   * - 2
     - ``ebank.put_utdq_stations``
     - add station locations
   * - 3
     - ``ebank.put_utdq_picks``
     - build the picks and apply QC
   * - 4
     - ``build_manifests``
     - build the tables, with your network's metadata
   * - 5
     - ``publish_flat_manifests``
     - prepare the files for upload
   * - 6
     - ``utdquake.publish_network``
     - open a pull request on Hugging Face
   * - 7-8
     - *optional*
     - travel-time model; figures for the documentation

**Before you start**

- ``pip install utdquake`` and a `Hugging Face token <https://huggingface.co/settings/tokens>`_
  (``export HF_TOKEN=hf_xxx``), needed only in step 6.
- **Depths must be in meters below sea level** (QuakeML ``Origin.depth``). If your catalog gives depth
  below the surface or a well reference, subtract that elevation first.
- Each pick needs a ``waveform_id`` with network and station codes.
- Name your network (``utdq_net``): the agency's code for an agency catalog (``CM``, ``tx``), or the next
  free ``R`` code (``R10``, ...) for a research catalog.

1. Event bank
^^^^^^^^^^^^^

.. code-block:: python

   from utdquake.bank.bank import UTDQBank
   from utdquake.core.config import get_utdq_paths

   ebank = UTDQBank(base_path=str(get_utdq_paths("CM")["banks"]),   # the folder name is the utdq_net
                    path_structure="{year}/{month}/{day}",
                    name_structure="{event_id_end}", format="quakeml")

   ebank.put_events(cat)                                    # an ObsPy Catalog, or:
   # ebank.put_utdq_events_from_folder("/path/to/quakeml", file_extension="*.xml")

2. Stations
^^^^^^^^^^^

A table with ``network`` (FDSN code), ``station``, ``latitude``, ``longitude``, ``elevation``, e.g. from
StationXML:

.. code-block:: python

   import obsplus
   from obspy import read_inventory

   stations = obsplus.stations_to_df(read_inventory("/path/to/network.xml"))
   stations = stations.drop_duplicates(["network", "station"])[
       ["network", "station", "latitude", "longitude", "elevation"]]
   ebank.put_utdq_stations(stations, calculate_d_az=True)

3. Picks and QC
^^^^^^^^^^^^^^^

.. code-block:: python

   ebank.put_utdq_picks(apply_utdq_qc=True)   # QC criteria: see the table in the quickstart

4. Tables and metadata
^^^^^^^^^^^^^^^^^^^^^^

``catalog``, ``catalog_type`` (``agency``, ``research`` or ``synthetic``) and ``dataset_version`` are
**required**: publishing refuses without them. ``uploaded_by_github`` should be your GitHub profile URL.

.. code-block:: python

   import pandas as pd
   from utdquake.writers.parquet import build_manifests

   info = pd.DataFrame({
       "utdq_net": ["CM"],
       "catalog": ["SGC"], "catalog_type": ["agency"], "dataset_version": ["v2"],
       "provider": ["SGC"], "provider_url": ["https://www.sgc.gov.co"],
       "country": ["Colombia"], "agency": ["Servicio Geologico Colombiano"],
       "continent": ["South America"],
       "uploaded_by_github": ["https://github.com/<your-username>"],
       "contact_email": ["you@example.com"], "doi": [None],
   })
   build_manifests(utdq_nets=["CM"], include_events=True, include_stations=True,
                   include_picks=True, include_networks=True, overwrite=True,
                   include_manual_network_info=info)

5. Prepare and 6. publish
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import utdquake as utdq
   from utdquake.writers.parquet import publish_flat_manifests

   publish_flat_manifests()
   utdq.publish_network("CM", create_pr=True)   # opens a pull request; the maintainer reviews and merges

The pull request contains the tables, the zipped event bank and the network row, in one commit. Maintainers
can drop ``create_pr=True`` to commit directly; ``utdq.remove_network("CM", create_pr=True)`` retires a
network.

7. Travel-time model (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adds ``travel_time_zscore`` to the picks and enables the travel-time figures:

.. code-block:: python

   from utdquake.qc.travel_time import build_travel_time_model

   build_travel_time_model("CM")
   utdq.publish_network("CM", include_travel_time=True, create_pr=True)

8. Figures for the documentation (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Needs a `GitHub token <https://github.com/settings/tokens>`_ with the **repo** scope
(``export GITHUB_TOKEN=ghp_xxx``) and ``pip install cartopy``. Opens a pull request that adds your network
to :ref:`overview-section`:

.. code-block:: python

   utdq.generate_network_figures("CM")
   utdq.publish_network_figures("CM")

Once merged, load your network like any other:

.. code-block:: python

   net = utdq.Dataset().get_network("CM")
