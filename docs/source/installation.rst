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