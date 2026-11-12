.. _installation-section:
Installation & Configuration
============================

Installing via pip
----------------------------
You can install `UTDQuake <https://pypi.org/project/utdquake/>`_ directly from PyPI using `pip`. 
This will install the Python package and its dependencies.

.. code-block:: bash

   pip install utdquake

The maps of the figures (``plot_overview``, ``generate_network_figures``, ...) need
`Cartopy <https://cartopy.readthedocs.io>`_, which is not installed with the package:

.. code-block:: bash

   pip install cartopy

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

- **Dataset versions** (``v1.0``, ``v2.0``, ``v2.1``, ...) are tags of the
  `Hugging Face repository <https://huggingface.co/datasets/ecastillot/UTDQuake>`_. A released version never
  changes. ``main`` holds the latest data: the last release plus the networks added since, which go into the
  next release.
- **Package versions** (``1.0.0``, ...) are releases of ``utdquake`` on
  `PyPI <https://pypi.org/project/utdquake/>`_. A package reads every dataset version from ``v1.0`` on.

How the dataset is numbered, what each version contains and how data is added between releases:
:ref:`versions-section`.

**Reading a version.** By default the latest data (``main``) is read. To reproduce a result, e.g. the one of
a paper, read a released version:

.. code-block:: python

   import utdquake

   dataset = utdquake.Dataset(version="v2.0")          # or Network("tx", version="v1.0")
   # same as: os.environ["UTDQUAKE_REVISION"] = "v2.0" (or revision= in download_snapshot / load)

The version applies to everything read or downloaded afterwards in the session.

**Where downloads go.** In the default cache each version has its own folder (``~/.utdquake/v2.0``,
``~/.utdquake/main``, ...), so files of different versions are never mixed and a new version is downloaded
fresh. A folder set with ``UTDQUAKE_ROOT`` is used as is, for whatever version you read: keep one version per
folder (a warning is logged when files of another version are downloaded into it). Each folder records the
version and Hub commit it was downloaded from in ``.utdquake/snapshot.json``. Event banks are downloaded only
when used (``Network(...).bank``).
