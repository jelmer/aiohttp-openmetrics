#!/usr/bin/python3

import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst'), 'r') as f:
    long_description = f.read()

setup(name="aiohttp-openmetrics",
      description="OpenMetrics provider for aiohttp",
      long_description=long_description,
      version='0.0.5',
      author="Jelmer Vernooij",
      author_email="jelmer@jelmer.uk",
      license="Apache v2 or later",
      url="https://github.com/jelmer/aiohttp-openmetrics/",
      install_requires=[
          'aiohttp',
          'prometheus_client',
      ],
      packages=['aiohttp_openmetrics'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Operating System :: POSIX',
      ])
