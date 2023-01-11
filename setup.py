###############################################################################
# Copyright 2019-2020 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open("README.md", "r") as readme_file:
    LONG_DESC = readme_file.read()

about = {}
with open(os.path.join("hepbenchmarksuite", "__version__.py")) as info:
    exec(info.read(), about)

setup(
    name=about["__title__"],
    version=about["__version__"],
    description=about["__description__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    long_description=LONG_DESC,
    long_description_content_type="text/markdown",
    url=about['__url__'],
    license=about['__license__'],
    scripts=['bin/bmkrun', 'bin/bmk_show_metadata'],
    packages=['hepbenchmarksuite', 'hepbenchmarksuite.plugins', 'hepbenchmarksuite.config'],
    package_data={'hepbenchmarksuite': ['config/*.yml']},
    python_requires='~=3.4',
    install_requires=['pip>=21.3.1', 'pyyaml>=5.1', 'stomp.py<=7.0.0', 'importlib-metadata', 'pyOpenSSL>=21.0.0']
)
