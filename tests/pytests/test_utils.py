#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import contextlib
import difflib
import os
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from hepbenchmarksuite.plugins.extractor import Extractor

import pytest
import yaml
from schema import Schema

from hepbenchmarksuite import utils


def test_prepare_metadata():
    """Test the preparation of metadata."""

    try:
        with open("hepbenchmarksuite/config/benchmarks.yml", "r") as cfg_file:
            sample_config = yaml.full_load(cfg_file)

    except FileNotFoundError:
        print("Failed to load configuration file.")
        sys.exit(1)

    # Set ncores since by default is commented
    sample_config["global"]["ncores"] = 2

    extra = {
        "start_time": "",
        "end_time": "",
    }

    # Generate metadata
    extractor = Extractor(sample_config['global'])
    meta_json = utils.prepare_metadata(sample_config, extra, extractor)

    # Drop HW and SW metadata keys sinc this json structure
    # is already covered in another test hw_metadata
    del meta_json["host"]["HW"]
    del meta_json["host"]["SW"]
    print(meta_json)

    # Define suite metadata schema
    metadata_schema = Schema(
        {
            str: str,
            "suite": {
                str: str,
                "benchmark_version": {str: str},
                "flags": {str: str, "ncores": int},
            },
            "host": {
                str: str,
                "tags": {str: str},
            },
        },
    )

    # Perform assertion test
    metadata_schema.validate(meta_json)


def test_get_tags_env():
    """Test get tags from env variables."""

    # Test no tags in env
    assert utils.get_tags_env() == {}

    # Test tags in env variables
    valid_dict = {"tag1": "value1", "tag2": "value2"}

    os.environ["BMKSUITE_TAG_TAG1"] = "value1"
    os.environ["BMKSUITE_TAG_TAG2"] = "value2"
    os.environ["BMKSUITE_TAGtypo_TAG3"] = "value3"

    assert utils.get_tags_env() == valid_dict


def test_run_separated_commands__valid_commands():
    cmd = 'echo test ; echo test'
    _, reply, _ = utils.run_separated_commands(cmd)
    assert reply == 'testtest'


@patch("hepbenchmarksuite.utils.run_piped_commands", return_value=(None, None, 'Command not found: dummy'))
def test_run_separated_commands__unknown_command(patch):
    cmd = 'dummy'
    _, reply, error = utils.run_separated_commands(cmd)
    assert len(error) > 0


@patch("hepbenchmarksuite.utils.run_piped_commands", return_value=(1, '', 'error message'))
def test_run_separated_commands__nonzero_return_code(patch):
    cmd = 'dummy ; dummy'
    return_code, reply, error = utils.run_separated_commands(cmd)
    assert return_code == 1
    assert reply == ''
    assert error == 'error message'


@pytest.mark.parametrize("cmd_str", ["cat /proc/minfo | grep MemTotal", "lxcpu"])
def test_exec_cmd_fail(cmd_str):
    """Test exec for failures."""

    result, return_code = utils.exec_cmd(cmd_str)

    print(result, return_code)

    assert return_code != 0


@pytest.mark.parametrize("cmd_str", ["cat /proc/meminfo | grep MemTotal", "uptime"])
def test_exec_cmd_success(cmd_str):
    """Test exec for success."""

    result, return_code = utils.exec_cmd(cmd_str)

    print(result, return_code)

    assert return_code == 0


def test_bench_versions():
    """Test parsing of benchmark versions."""

    try:
        with open("hepbenchmarksuite/config/benchmarks.yml", "r") as cfg_file:
            sample_config = yaml.full_load(cfg_file)

    except FileNotFoundError:
        print("Failed to load configuration file.")
        sys.exit(1)

    # Override benchmark list
    sample_config["global"]["benchmarks"] = [
        "db12",
        "hs06",
        "hepscore",
        "spec2017",
        "newbench",
    ]

    # Valid benchmark version that should be printed
    valid_version_output = {
        "db12": "v0.1",
        "hepscore": "v1.2",
        "hs06": "v2.1",
        "spec2017": "v2.1",
        "newbench": "not_available",
    }
    print(utils.bench_versions(sample_config))

    assert utils.bench_versions(sample_config) == valid_version_output


def test_export_creation():
    """Test the export directory from utils."""

    # File extensions
    file_extensions = [".json", ".yaml", ".log", ".txt", ".ini", ".logg"]

    # Create a temporary directory
    # It will finalize automatically after context end
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        print("Created temporary directory:", tmp_dir_path)

        # Create temporary files
        for ext in file_extensions:
            fd, path = tempfile.mkstemp(suffix=ext, dir=tmp_dir_path)
            print(fd, path)

        # Check if compressed file was created
        assert utils.export(tmp_dir_path, "compressed_file.tgz") == 0


def test_export_valid():
    """Test if the contents of exported compressed file are valid."""

    with tarfile.open("compressed_file.tgz", "r:gz") as archive:
        print(archive.list())
        print(archive.getnames())

        # It should only contain two files in this compressed file: json, log
        # better logic can be added in the future if needed
        assert len(archive.getnames()) == 2

    # Clean-up
    os.remove("compressed_file.tgz")


def test_print_results():
    """Test the print results from utils."""
    # Temporary file
    TEMP_FILE = "result_dump"

    # Create a context to redirect the stdout output
    # from utils.print_results_from_file to a file
    # that can be later accessed for comparison
    with open(TEMP_FILE, "w") as tmp_file:
        with contextlib.redirect_stdout(tmp_file):
            utils.print_results_from_file("tests/data/result_profile_sample.json")

    # Open a valid print results sample file
    with open("tests/data/valid_print_results_sample", "r") as print_sample:
        # Open the file with the output generated from previous call
        with open(TEMP_FILE, "r") as gen_out:
            sample_output = print_sample.readlines()
            utils_output = gen_out.readlines()

            # Compare differences between sample print message
            # and the one resulting from utils print function
            diff = difflib.Differ().compare(sample_output, utils_output)

            # Dump the printout for easier identification of issues
            sys.stdout.writelines(diff)

            assert sample_output == utils_output


@pytest.mark.parametrize(
    "url", ["httpps://brokenlink1", "httpss://brokenlink2", "brokenlink3.com"]
)
def test_failed_download(url):
    """Test the download failure."""
    assert utils.download_file(url, "test") == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite/-/raw/qa/README.md",
        "https://gitlab.cern.ch/hep-benchmarks/hep-score/-/raw/master/README.md",
    ],
)
@pytest.fixture(scope="session")
def test_success_download(url, tmpdir_factory):
    """Test the download success."""
    assert (
            utils.download_file(url, tmpdir_factory.mktemp().join("downloaded_README.md"))
            == 0
    )
    assert os.path.isfile("downloaded_README.md") == 1


if __name__ == "__main__":
    unittest.main(verbosity=2)
