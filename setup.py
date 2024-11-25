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
    # Remove 'scripts' field
    packages=['hepbenchmarksuite',
              'hepbenchmarksuite.plugins',
              'hepbenchmarksuite.plugins.construction',
              'hepbenchmarksuite.plugins.execution',
              'hepbenchmarksuite.plugins.registry',
              'hepbenchmarksuite.config'],
    package_data={'hepbenchmarksuite': ['config/*.yml']},
    python_requires='~=3.6',
    install_requires=['beautifulsoup4', 'importlib-metadata', 'pem', 'pip>=21.3.1',
                      'pyOpenSSL>=21.0.0', 'pyyaml>=5.1', 'requests', 'stomp.py<=7.0.0', 'numpy',
                      'distro', 'opensearch-py'],
    # Add 'entry_points' for console scripts
    entry_points={
        'console_scripts': [
            'bmkrun = hepbenchmarksuite.bmkrun:main',
            'bmk_show_metadata = hepbenchmarksuite.bmk_show_metadata:main',
            'bmksend = hepbenchmarksuite.bmksend:main',
        ],
    },
)

