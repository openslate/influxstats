#!/usr/bin/env python
import configparser
import os

from setuptools import find_packages, setup

packages = find_packages("src")


def readme():
    with open("README.md") as f:
        return f.read()


def get_required_packages():
    """
    Returns the packages used for install_requires

    This used to pin down every package in Pipfile.lock to the version, but that, in turn, broke
    downstream projects because it was way too strict.  Instead, this pins packages pinned in Pipfile.
    """
    config = configparser.ConfigParser(strict=False)
    config.read("Pipfile")

    # when the Pipfile specifies a package, constrain it to that version
    install_requires = []
    for package, version in config["packages"].items():
        full_package = package
        package_version = None

        if version[0] == "{":
            uncurled = version[1:-1]
            uncurled_split = [x.strip() for x in uncurled.split(",")]

            # find the version
            for item in uncurled_split:
                if "version" in item:
                    item_split = [x.strip() for x in item.split("=", 2)]

                    version = item_split[1][1:-1]
                    if version != "*":
                        package_version = version

                    break
        elif version != '"*"':
            package_version = version[1:-1]

        if package_version:
            full_package = f"{package}{package_version}"

        install_requires.append(full_package)

    return install_requires


setup(
    name="influxstats",
    url="https://github.com/openslate/influxstats",
    author="Openslate",
    author_email="code@openslate.com",
    description="Create consistent stats across your entire codebase",
    long_description=readme(),
    long_description_content_type="text/markdown",
    use_scm_version=True,
    packages=packages,  # include all packages under src
    package_dir={"": "src"},  # tell distutils packages are under src
    install_requires=get_required_packages(),
)
