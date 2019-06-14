#!/usr/bin/env python
from __future__ import unicode_literals

import argparse
import json
import logging
import os
import shutil
import sys
import tarfile
from builtins import bytes
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from tempfile import mkdtemp

TEMPLATE_PATH = Path(__file__).parents[1] / "template"

logger = logging.getLogger(__name__)


def add_entity_subparser(subparsers):
    entity_parser = subparsers.add_parser("entity")
    entity_parser.add_argument("entity_name", type=str,
                               help="Name of the gazetteer entity")
    entity_parser.add_argument("language", type=str,
                               help="Language of the gazetteer entity")
    entity_parser.add_argument("version", type=str,
                               help="Version of the resource")
    entity_parser.add_argument("-d", "--description", type=str,
                               help="Description of the resource")
    entity_parser.add_argument(
        "-v", "--snips_nlu_version", type=str,
        help="Compatible versions of snips-nlu e.g. '>=0.1.0,<1.0.0'")
    entity_parser.add_argument("-l", "--license", type=str,
                               help="License of the gazetteer entity data")
    entity_parser.add_argument("gazetteer_path", type=str,
                               help="Path of the gazetteer entity directory")
    entity_parser.add_argument("output_filename", type=str,
                               help="Output archive file name")
    entity_parser.set_defaults(func=generate_entity_archive)
    return entity_parser


def add_resources_subparser(subparsers):
    resources_parser = subparsers.add_parser("resources")
    resources_parser.add_argument("language", type=str,
                                  help="Language of the resource")
    resources_parser.add_argument("version", type=str,
                                  help="Version of the resource")
    resources_parser.add_argument("-d", "--description", type=str,
                                  help="Description of the resource")
    resources_parser.add_argument(
        "-v", "--snips_nlu_version", type=str,
        help="Compatible versions of snips-nlu e.g. '>=0.1.0,<1.0.0'")
    resources_parser.add_argument("-l", "--license", type=str,
                                  help="License of the language resources")
    resources_parser.add_argument(
        "resources_directory", type=str,
        help="Path to the language resources directory")
    resources_parser.add_argument("output_filename", type=str,
                                  help="Output archive file name")
    resources_parser.set_defaults(func=generate_language_resources_archive)
    return resources_parser


def generate_entity_archive(
        entity_name, language, version, description, snips_nlu_version,
        license, gazetteer_path, output_filename):
    if not entity_name.startswith('snips/'):
        raise ValueError(
            "Gazetteer entity '{e}' isn't valid. Entity names must start with "
            "'snips/'".format(e=entity_name))
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


def generate_language_resources_archive(
        language, version, description, snips_nlu_version, license,
        resources_directory, output_filename):
    if description is None:
        description = "Language resources for '%s'" % language
    if snips_nlu_version is None:
        snips_nlu_version = ">=0.1.0,<1.0.0"
    if license is None:
        license = "Apache License, Version 2.0"
    with temp_dir() as tmp_path:
        package_name_with_version = _build_language_resources_package(
            language, version, description, license, snips_nlu_version,
            Path(resources_directory), tmp_path)
        make_tarfile(output_filename,
                     str(tmp_path / package_name_with_version))


def _build_language_resources_package(
        language, version, description, license, snips_nlu_version,
        resources_directory, tmp_path):
    package_name = "snips_nlu_{l}".format(l=language)
    package_name_with_version = "{p}-{v}".format(p=package_name, v=version)
    logger.info("Copying template to %s ..." % tmp_path)
    temp_subdir = tmp_path / package_name_with_version
    shutil.copytree(str(TEMPLATE_PATH), str(temp_subdir))
    logger.info("Updating template files ...")
    metadata_json_path = temp_subdir / "metadata.json"
    with metadata_json_path.open(encoding="utf8") as f:
        template_metadata = json.load(f)

    if not (resources_directory / "noise.txt").exists():
        logger.error("No noise found in %s" % resources_directory)
        raise FileNotFoundError(str(resources_directory / "noise"))
    if not (resources_directory / "stop_words.txt").exists():
        logger.error("No stop words found in %s" % resources_directory)
        raise FileNotFoundError(str(resources_directory / "stop_words"))

    gazetteers = [
        f.stem for f in (resources_directory / "gazetteers").glob("*.txt")]
    word_clusters = [
        f.stem for f in (resources_directory / "word_clusters").glob("*.txt")]

    stems = None
    if (resources_directory / "stemming" / "stems.txt").exists():
        stems = "stems"

    metadata = {
        "name": package_name,
        "language": language,
        "version": version,
        "description": description,
        "snips_nlu_version": snips_nlu_version,
        "author": template_metadata["author"],
        "email": template_metadata["email"],
        "url": template_metadata["url"],
        "license": license,
        "gazetteers": gazetteers,
        "word_clusters": word_clusters,
        "stems": stems,
        "noise": "noise",
        "stop_words": "stop_words",
    }

    metadata_bytes = bytes(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf8")
    with metadata_json_path.open(encoding="utf8", mode="w") as f:
        f.write(metadata_bytes.decode("utf8"))
    package_dir = temp_subdir / package_name
    shutil.move(str(temp_subdir / "snips_nlu_xx"), str(package_dir))
    subpackage_dir = package_dir / package_name_with_version
    subpackage_dir.mkdir()

    def ignore_non_txt_files(_, files):
        return [file for file in files if not file.endswith(".txt")]

    if gazetteers:
        logger.info("Copying gazetteers: %s ..." % gazetteers)
        shutil.copytree(str(resources_directory / "gazetteers"),
                        str(subpackage_dir / "gazetteers"),
                        ignore=ignore_non_txt_files)
    else:
        logger.warning("No gazetteers found")
    if word_clusters:
        logger.info("Copying word clusters: %s ..." % word_clusters)
        shutil.copytree(str(resources_directory / "word_clusters"),
                        str(subpackage_dir / "word_clusters"),
                        ignore=ignore_non_txt_files)
    else:
        logger.warning("No word clusters found")
    if stems:
        (subpackage_dir / "stemming").mkdir()
        logger.info("Copying stems...")
        shutil.copy(str(resources_directory / "stemming" / "stems.txt"),
                    str(subpackage_dir / "stemming" / "stems.txt"))
    else:
        logger.warning("No stems found")
    logger.info("Copying noise...")
    shutil.copy(str(resources_directory / "noise.txt"),
                str(subpackage_dir))
    logger.info("Copying stop_words...")
    shutil.copy(str(resources_directory / "stop_words.txt"),
                str(subpackage_dir))
    return package_name_with_version


def _build_entity_package(entity_name, language, version, description, license,
                          snips_nlu_version, gazetteer_path, tmp_path):
    entity_short_name = get_entity_short_name(entity_name)
    package_name = "snips_nlu_{n}_{l}".format(n=entity_short_name, l=language)
    package_name_with_version = "{p}-{v}".format(p=package_name, v=version)
    logger.info("Copying template to %s ..." % tmp_path)
    temp_subdir = tmp_path / package_name_with_version
    shutil.copytree(str(TEMPLATE_PATH), str(temp_subdir))
    logger.info("Updating template files ...")
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
    logger.info("Creating tar archive ...")
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


@contextmanager
def temp_dir():
    tmp_dir = mkdtemp()
    try:
        yield Path(tmp_dir)
    finally:
        shutil.rmtree(tmp_dir)


def get_entity_short_name(entity_name):
    # snips/musicArtist -> musicartist
    return entity_name[6:].lower()


def set_logger(level):
    logger_ = logging.getLogger(__name__)
    formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger_.addHandler(handler)
    logger_.setLevel(level)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Utility to generate archives for Snips NLU",
        prog="python -m cli.generate_archive")
    subparsers_ = arg_parser.add_subparsers(help="types of archives")
    add_entity_subparser(subparsers_)
    add_resources_subparser(subparsers_)
    cmdline_arguments = arg_parser.parse_args()

    set_logger(logging.INFO)

    if hasattr(cmdline_arguments, "func"):
        kwargs = deepcopy(cmdline_arguments.__dict__)
        kwargs.pop("func")
        cmdline_arguments.func(**kwargs)
    else:
        # user has not provided a subcommand, let's print the help
        arg_parser.print_help()
        exit(1)
