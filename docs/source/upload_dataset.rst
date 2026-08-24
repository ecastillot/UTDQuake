.. _upload-dataset-section:
Upload your dataset
============================

This guide turns a catalog you already have -- an ObsPy
:class:`~obspy.core.event.Catalog`, or a folder of QuakeML files -- into a
network published on the shared
`UTDQuake Hugging Face dataset <https://huggingface.co/datasets/ecastillot/UTDQuake>`_,
so anyone can load it with :func:`utdquake.load`.

There are six required steps: 1-5 build everything locally, and step 6
uploads it. Two more are optional, for the documentation site: step 7 adds
the travel-time z-score, and step 8 adds the figures shown in
:ref:`overview-section`.

.. list-table::
   :widths: 8 20 40
   :header-rows: 1

   * - Step
     - Function
     - What it does
   * - 1
     - ``ebank.put_events(...)``
     - loads your Catalog / QuakeML files into an event bank
   * - 2
     - ``ebank.put_utdq_stations(...)``
     - attaches station locations, computes distance/azimuth
   * - 3
     - ``ebank.put_utdq_picks(...)``
     - builds the picks table and applies QC
   * - 4
     - ``build_manifests(...)``
     - builds the ``events`` / ``stations`` / ``picks`` / ``network`` tables
   * - 5
     - ``publish_flat_manifests(...)``
     - lays those tables out for publishing
   * - 6
     - ``utdquake.publish_network(...)``
     - uploads to the Hub

Prerequisites
^^^^^^^^^^^^^

.. code-block:: bash

   pip install utdquake
   export HF_TOKEN=hf_xxx   # or run `huggingface-cli login` once instead

``HF_TOKEN`` is only needed for step 6 (Steps 1-5 are entirely local). It
authenticates you with `Hugging Face <https://huggingface.co>`_, the site
that hosts the dataset. If you don't have an account yet, sign up for free at
`huggingface.co/join <https://huggingface.co/join>`_, then create a token by
following Hugging Face's own guide,
`User access tokens <https://huggingface.co/docs/hub/security-tokens>`_
(or go straight to `huggingface.co/settings/tokens <https://huggingface.co/settings/tokens>`_
once logged in).

1. Load your events into an event bank
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Everything below reads from a :class:`utdquake.bank.bank.UTDQBank` rather than
from your Catalog or files directly, so the first step is loading your events
into one. The bank's directory name *is* your network code -- a bank at
``.../banks/CM`` publishes as network ``"CM"``.

.. code-block:: python

   from utdquake.bank.bank import UTDQBank
   from utdquake.core.config import get_utdq_paths

   NETWORK = "CM"
   bank_path = get_utdq_paths(NETWORK)["banks"]   # .../banks/CM

   ebank = UTDQBank(
       base_path=str(bank_path),
       path_structure="{year}/{month}/{day}",
       name_structure="{event_id_end}",
       format="quakeml",
   )

Then load your events in, whichever form you have them in:

.. code-block:: python

   # If you already have an ObsPy Catalog:
   # cat = obspy.read_events(...) / built from an FDSN client / etc.
   ebank.put_events(cat)

   # If you have a folder of QuakeML files instead:
   ebank.put_utdq_events_from_folder("/path/to/quakeml_folder", file_extension="*.xml")

Either way, each ``Pick`` needs a ``waveform_id`` with a network and station
code (standard for QuakeML/FDSN picks) -- step 2 uses it to look up that
station's location.

2. Attach station metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Give it a table with at least ``network``, ``station``, ``latitude``,
``longitude`` -- from a StationXML inventory, an FDSN station query, or your
own table:

.. code-block:: python

   import obsplus
   from obspy import read_inventory

   inv = read_inventory("/path/to/network.xml")
   stations_df = obsplus.stations_to_df(inv)
   stations_df = (
       stations_df.sort_values("start_date")
       .drop_duplicates(subset=["network", "station"], keep="first")
       [["network", "station", "latitude", "longitude", "elevation"]]
   )

   ebank.put_utdq_stations(stations_df, calculate_d_az=True)

3. Compute picks and apply QC
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   ebank.put_utdq_picks(apply_utdq_qc=True)

This filters out picks/events that fail UTDQuake's minimum QC criteria (see
the table in :ref:`quickstart-section`) and saves the resulting picks table.

4. Build the manifest tables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from utdquake.writers.parquet import build_manifests

   build_manifests(
       networks=["CM"],
       include_events=True,
       include_stations=True,
       include_picks=True,
       include_networks=True,
       overwrite=True,
   )

This builds the four tables from everything computed in steps 1-3.

Some network-level fields simply can't be derived from picks/events --
``provider``, ``provider_url``, ``country``, ``agency``, ``continent`` --
there's no way to infer "who operates this network" from the data itself. Add
those yourself with ``include_manual_network_info``:

.. code-block:: python

   import pandas as pd

   manual_info = pd.DataFrame({
       "network": ["CM"],
       "provider": ["SGC"],
       "provider_url": ["https://www.sgc.gov.co"],
       "country": ["Colombia"],
       "agency": ["Servicio Geologico Colombiano"],
       "continent": ["South America"],
   })

   build_manifests(
       networks=["CM"],
       include_networks=True,
       overwrite=True,
       include_manual_network_info=manual_info,
   )

5. Lay out for publishing
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from utdquake.writers.parquet import publish_flat_manifests

   publish_flat_manifests()

6. Publish
^^^^^^^^^^

Most contributors won't have write access to the shared repo -- and don't
need it. Publish with ``create_pr=True``, which opens a Pull Request instead
of committing directly, using the same token from Prerequisites (a **read**
token is enough for this):

.. code-block:: python

   import utdquake as utdq

   utdq.publish_network("CM", create_pr=True)

The maintainer reviews the PR on the
`dataset's Hugging Face page <https://huggingface.co/datasets/ecastillot/UTDQuake>`_
and merges it. ``remove_network(..., create_pr=True)`` works the same way for
retiring a network.

If you already have write access
"""""""""""""""""""""""""""""""

Drop ``create_pr=True`` to commit directly instead of opening a PR:

.. code-block:: python

   import utdquake as utdq

   utdq.publish_network("CM")
   # utdq.remove_network("CM")   # to undo / retire a network

Either way, ``publish_network`` bundles every file -- the per-network shards
and the shared ``network.parquet`` -- into a single commit, so a network is
never left half-published. It also uploads the local EventBank (zipped) by
default (``include_banks=True``), since ``Network.events``/``.stations``/``.picks``
require the bank locally to resolve at all -- pass ``include_banks=False``
explicitly if you're re-publishing a network whose local bank no longer
exists on disk.

7. Build a travel-time model (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your dataset is already complete and usable without this. It's only needed
if you want ``travel_time_zscore`` filled in on the picks table, or the
travel-time QC figures (step 8) to work.

.. code-block:: python

   from utdquake.qc.travel_time import build_travel_time_model

   build_travel_time_model("CM")

This fits a travel-time model per phase from the picks built in step 3,
saves it locally, and updates the local picks table with a
``travel_time_zscore`` column. Since you already published in step 6,
publish again to push the update -- add ``include_travel_time=True`` this
time so the model itself is uploaded too, not just the updated picks table:

.. code-block:: python

   import utdquake as utdq

   utdq.publish_network("CM", include_travel_time=True, create_pr=True)

8. Add your network to the documentation (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The figures shown in :ref:`overview-section` live on GitHub (a different
site from Hugging Face, where the dataset itself lives), so this is a
separate, optional step -- your dataset is already fully usable without it.

If you don't already have a `GitHub <https://github.com>`_ account, sign up
for free at `github.com/join <https://github.com/join>`_. GitHub calls its
version of what we set up in Prerequisites a "personal access token." To
create one:

1. Go to `github.com/settings/tokens <https://github.com/settings/tokens>`_
   (you'll need to log in first).
2. Click **Generate new token** → **Generate new token (classic)**.
3. Give it any name you'll recognize later, e.g. "utdquake".
4. Under **Select scopes**, check the box next to **repo** (this is what
   lets it create the PR on your behalf).
5. Click **Generate token** and copy it -- GitHub only shows it once.

Then, same as with ``HF_TOKEN``:

.. code-block:: bash

   export GITHUB_TOKEN=ghp_xxx

.. code-block:: python

   import utdquake as utdq

   utdq.generate_network_figures("CM")   # saves the figures to ./figures/CM
   utdq.publish_network_figures("CM")    # opens a PR (or commits, if you're a maintainer)

The maintainer reviews and merges the PR the same way as the dataset PR
earlier. Until it's merged, :ref:`overview-section` shows that network as
*pending* rather than a broken image.

Next steps
^^^^^^^^^^

Once published (or merged, if you opened a PR), load your network like any
other in :ref:`quickstart-section`:

.. code-block:: python

   import utdquake as utdq

   net = utdq.Dataset().get_network("CM")
   display(net.events)
