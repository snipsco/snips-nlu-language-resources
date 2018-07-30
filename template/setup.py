#!/usr/bin/env python
# coding: utf8
from __future__ import unicode_literals

import io
import json
from os import path, walk
from shutil import copy

from setuptools import setup


def list_files(data_dir):
    filepaths = []
    for root, _, filenames in walk(data_dir):
        for filename in filenames:
            if not filename.startswith("."):
                filepaths.append(path.join(root, filename))
    root_dir = path.dirname(data_dir)
    filepaths = [path.relpath(p, root_dir) for p in filepaths]
    filepaths.append("metadata.json")
    return filepaths


def setup_package():
    root = path.abspath(path.dirname(__file__))
    metadata_path = path.join(root, "metadata.json")
    with io.open(metadata_path, encoding="utf8") as f:
        metadata = json.load(f)
    resources_name = str(metadata["name"])
    version = metadata["version"]
    resources_dir = path.join(resources_name, resources_name + "-" + version)

    copy(metadata_path, path.join(resources_name))
    copy(metadata_path, resources_dir)

    setup(
        name=resources_name,
        version=metadata["version"],
        description=metadata.get("description"),
        author=metadata.get("author"),
        author_email=metadata.get("email"),
        url=metadata.get("url"),
        license=metadata.get("license"),
        packages=[resources_name],
        package_data={resources_name: list_files(resources_dir)},
        zip_safe=False,
    )


if __name__ == "__main__":
    setup_package()
