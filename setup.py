from setuptools import setup, find_packages
import pathlib

import pkg_resources
import setuptools
import codecs
import os

# here = os.path.abspath(os.path.dirname(__file__))

# with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
#     long_description = "\n" + fh.read()

VERSION = '0.0.1'
DESCRIPTION = 'UTD Earthquake Dataset'

req_path = os.path.join(os.path.dirname(__file__),"requirements.txt")
with pathlib.Path('requirements.txt').open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement
        in pkg_resources.parse_requirements(requirements_txt)
    ]

# Setting up
setup(
    name="UTDQuake",
    version=VERSION,
    author="ecastillot (Emmanuel Castillo)",
    author_email="<castillo.280997@gmail.com>",
    url="https://github.com/ecastillot/UTDQuake",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=install_requires,
    keywords=['python', "utd_eqd","earthquakes","seismology"],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
    ],
    python_requires='>=3.10'
)

# python setup.py sdist bdist_wheel
# twine upload dist/*
# python -m twine upload -u __token__ -p [unique_token] dist/*