from __future__ import unicode_literals

import json
import os
import shutil
import sys
import tarfile
from builtins import bytes

import plac
from utils import (
    TEMPLATE_PATH, get_entity_short_name, get_supported_entities, temp_dir)


@plac.annotations(
    entity_name=("Name of the gazetteer entity", "positional", None, str),
    language=("Language of the gazetteer entity", "positional", None, str),
    version=("Version of the resource", "positional", None, str),
    description=("Description of the resource", "option", "d", str),
    snips_nlu_version=(
            "Compatible versions of snips-nlu e.g. '>=0.1.0,<1.0.0'", "option",
            "v", str),
    license=("License of the gazetteer entity data", "option", "l", str),
    gazetteer_path=("Path of the gazetteer entity directory", "positional",
                    None, str),
    output_filename=("Output archive file name", "positional", None, str))
def generate_entity_archive(
        entity_name, language, version, description, snips_nlu_version,
        license, gazetteer_path, output_filename):
    supported_entities = get_supported_entities(language)
    if entity_name not in supported_entities:
        raise ValueError("Gazetteer entity '%s' not supported, available "
                         "entities: %s"
                         % (entity_name, ', '.join(supported_entities)))
    if description is None:
        description = "Resources for the '{e}' gazetteer entity in language " \
                      "'{l}'".format(e=entity_name, l=language)
    if snips_nlu_version is None:
        snips_nlu_version = ">=0.1.0,<1.0.0"
    if license is None:
        license = "Apache License, Version 2.0"
    with temp_dir() as tmp_path:
        package_name_with_version = _build_entity_package(
            entity_name, language, version, description, license,
            snips_nlu_version, gazetteer_path, tmp_path)
        make_tarfile(output_filename,
                     str(tmp_path / package_name_with_version))


def _build_entity_package(entity_name, language, version, description, license,
                          snips_nlu_version, gazetteer_path, tmp_path):
    entity_short_name = get_entity_short_name(entity_name)
    package_name = "snips_nlu_{n}_{l}".format(n=entity_short_name, l=language)
    package_name_with_version = "{p}-{v}".format(p=package_name, v=version)
    print("Copying template to %s ..." % tmp_path)
    temp_subdir = tmp_path / package_name_with_version
    shutil.copytree(str(TEMPLATE_PATH), str(temp_subdir))
    print("Updating template files ...")
    metadata_json_path = temp_subdir / "metadata.json"
    # Remove template metadata.json
    metadata_json_path.unlink()
    metadata = {
        "name": package_name,
        "language": language,
        "version": version,
        "entity_name": entity_name,
        "data_directory": entity_short_name,
        "description": description,
        "snips_nlu_version": snips_nlu_version,
        "license": license
    }
    metadata_bytes = bytes(json.dumps(metadata, indent=2, sort_keys=True),
                           encoding="utf8")
    with metadata_json_path.open(encoding="utf8", mode="w") as f:
        f.write(metadata_bytes.decode("utf8"))
    package_dir = temp_subdir / package_name
    shutil.move(str(temp_subdir / "snips_nlu_xx"), str(package_dir))
    subpackage_dir = package_dir / package_name_with_version
    subpackage_dir.mkdir()
    gazetteer_entity_dir = subpackage_dir / entity_short_name
    shutil.copytree(gazetteer_path, str(gazetteer_entity_dir))
    return package_name_with_version


def make_tarfile(output_filename, source_dir):
    print("Creating tar archive ...")
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


if __name__ == "__main__":
    plac.call(generate_entity_archive, sys.argv[1:])
