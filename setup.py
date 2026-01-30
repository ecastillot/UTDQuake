"""
Setup script for the UTDQuake Python package.

This script uses setuptools to define package metadata, dependencies,
and other configuration needed to build and distribute the package.
"""

from setuptools import setup, find_packages
import pathlib

import pkg_resources
import setuptools
import codecs
import os

import utdquake

VERSION = utdquake.__version__

DESCRIPTION = 'University of Texas at Dallas Earthquake Dataset'

# Read requirements.txt and parse them into a list for install_requires
req_path = os.path.join(os.path.dirname(__file__),"requirements.txt")
readme_path = os.path.join(os.path.dirname(__file__),"README.md")
with pathlib.Path(req_path).open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement
        in pkg_resources.parse_requirements(requirements_txt)
    ]

    
# Read the contents of your README file
with open(readme_path, "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Setting up
setup(
    name="utdquake",
    version=VERSION,
    author="ecastillot (Emmanuel Castillo)",
    author_email="<castillo.280997@gmail.com>",
    url="https://github.com/ecastillot/UTDQuake",
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=install_requires,
    keywords=['python', "utdquake","earthquakes","seismology"],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: Unix",
    ],
    python_requires='>=3.10'
)



# python setup.py sdist bdist_wheel
# twine upload dist/*
# python -m twine upload -u __token__ -p [unique_token] dist/*