#!/usr/bin/env python
import os

from setuptools import find_packages, setup

packages = find_packages('src')
print(packages)

setup(
    name='influxstats',
    url='https://github.com/openslate/influxstats',
    author='Openslate',
    author_email='code@osslabs.net',
    version='0.0.5',
    packages=packages,  # include all packages under src
    package_dir={'':'src'},   # tell distutils packages are under src

    install_requires=[
        'statsd',
    ]
)
