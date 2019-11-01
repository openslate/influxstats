#!/usr/bin/env python
import os

from setuptools import find_packages, setup

packages = find_packages("src")


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="influxstats",
    url="https://github.com/openslate/influxstats",
    author="Openslate",
    author_email="code@openslate.com",
    description="Create consistent stats across your entire codebase",
    long_description=readme(),
    long_description_content_type="text/markdown",
    version="0.0.0",
    packages=packages,  # include all packages under src
    package_dir={"": "src"},  # tell distutils packages are under src
    install_requires=["statsd"],
)
