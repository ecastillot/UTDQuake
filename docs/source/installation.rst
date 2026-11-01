.. _installation-section:
Installation & Configuration
============================

Installing via pip
----------------------------
You can install `UTDQuake <https://pypi.org/project/utdquake/>`_ directly from PyPI using `pip`. 
This will install the Python package and its dependencies.

.. code-block:: bash

   pip install utdquake

Configuration
----------------------------

UTDQuake requires a root data directory where it will store
all downloaded datasets, networks, stations, and events. 
By default, it uses a standard path in your home directory, 
but you can set a custom path using an environment variable.

.. code-block:: python

   import os
   os.environ["UTDQUAKE_ROOT"] = "/my/custom/path/for/utdquake_data"
   os.environ["UTDQUAKE_DAS_ROOT"] = "/my/custom/path/for/utdquake_DAS_data"

.. _installation-versions-subsection:

Versions
----------------------------

UTDQuake versions the data and the software separately:

- **Dataset versions** (``v1.0``, ``v2.0``, ...) are tags of the
  `Hugging Face repository <https://huggingface.co/datasets/ecastillot/UTDQuake>`_. A tagged version
  never changes. ``main`` always holds the latest data, including additions not yet released.
- **Package versions** (``1.0.0``, ...) are releases of ``utdquake`` on
  `PyPI <https://pypi.org/project/utdquake/>`_. Package 1.0 reads every dataset version from ``v1.0`` on.

By default the latest data (``main``) is downloaded. To reproduce a result, e.g. the one of a paper,
read a fixed version: set ``UTDQUAKE_REVISION`` to its tag before downloading, or pass ``revision=`` to
:func:`utdquake.download_snapshot` and :func:`utdquake.load`.

.. code-block:: python

   os.environ["UTDQUAKE_REVISION"] = "v1.0"

Every row records the version that added it (``dataset_version``), so the data of a version can also be
selected from the latest release.

**v2.0** *(in preparation)*

- New UTDQuake networks: ``CM`` (Servicio Geologico Colombiano) and the research catalogs ``R01``-``R08``.
- More events for the existing networks: up to 20,000 events per network after quality control,
  extended to 2026.

**v1.0** *(dataset of the UTDQuake paper)*

- 82 seismic networks and one DAS network (``UWF``): 346,487 earthquakes, 10.1 million P and S picks
  and 17,844 stations; 450 DAS earthquakes with 7.8 million picks on 22,500 channels.
- New layout: ``utdq_net`` names each UTDQuake network, ``network`` is the FDSN code of each station and
  ``catalog`` the source catalog.
- Stations reported by ISC with the placeholder code ``IR`` get their network and location from the ISC
  station registry.
- Picks are counted by phase label (P, Pg, Pn, S, Sg, Sn) and by phase family.

**v0.3** *(previous layout)*

- The dataset as published before version 1.0 (files ``network=<name>.parquet``), read by ``utdquake``
  0.3. Kept so earlier results can be reproduced.

See :ref:`versions-section` for the full list of changes of each version.