"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import json
import logging
import os
import socket
import subprocess
import sys
import tarfile
import uuid
import urllib.request
from urllib.error import HTTPError, URLError

from hepbenchmarksuite.plugins.extractor import Extractor
from hepbenchmarksuite import __version__

_log = logging.getLogger(__name__)


def download_file(url, outfile):
    """Download file from an url and save it locally.

    Args:
      url: String with the link to download.
      outfile: String with the filename to save.

    Returns:
      Error code: 0 OK , 1 Not OK
    """

    _log.info("Attempting to download remote config file...")

    # Download the config file from url and save it locally
    try:
        with urllib.request.urlopen(url) as response, open(outfile, 'wb') as fout:
            fout.write(response.read())
            _log.info("File saved: %s", fout.name)
            return 0

    except (ValueError, HTTPError, URLError):
        _log.error('Failed to download file from provided link: %s', url)
        return 1


def export(result_dir, outfile):
    """Export all json and log files from a given dir.

    Args:
      result_dir: String with the directory to compress the files.
      outfile:    String with the filename to save.

    Returns:
      Error code: 0 OK , 1 Not OK
    """
    _log.info("Exporting *.json, *.log from %s...", result_dir)

    with tarfile.open(outfile, 'w:gz') as archive:
        # Respect the tree hierarchy on compressing
        for root, dirs, files in os.walk(result_dir):
            for name in files:
                if name.endswith('.json') or name.endswith('.log'):
                    archive.add(os.path.join(root, name))

    _log.info("Files compressed! The resulting file was created: %s", outfile)

    return 0


def exec_wait_benchmark(cmd_str):
    """Accept command string to execute and waits for process to finish.

    Args:
      cmd_str: Command to execute.

    Returns:
      An POSIX exit code (0 through 255)
    """

    _log.debug("Excuting command: %s", cmd_str)

    cmd = subprocess.Popen(cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Output stdout from child process
    line = cmd.stdout.readline()
    while line:
        sys.stdout.write(line.decode('utf-8'))
        line = cmd.stdout.readline()

    # Wait until process is complete
    cmd.wait()

    # Check for errors
    if cmd.returncode != 0:
        _log.error("Benchmark execution failed; returncode = %s.", cmd.returncode)

    return cmd.returncode


def get_tags_env():
    """Get tags from user environment variables.

    Returns:
      A dict containing the tags.
    """

    tags = {}

    # Get ENV variables that start with BMKSUITE_TAG_[user-tag]
    # returns json with user-tag in lower case
    PREFIX = "BMKSUITE_TAG_"

    for key, val in os.environ.items():
        if PREFIX in key:
            _log.debug("Found tag in ENV: %s=%s", key, val)

            tag_key = key.replace(PREFIX, '').lower()

            tags[tag_key] = str(val)

    return tags


def exec_cmd(cmd_str):
    """Execute a command string and returns its output.

    Args:
      cmd_str: A string with the command to execute.

    Returns:
      A string with the output.
    """
    _log.debug("Excuting command: %s", cmd_str)

    cmd = subprocess.Popen(cmd_str, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd_reply, cmd_error = cmd.communicate()

    # Check for errors
    if cmd.returncode != 0:
        cmd_reply = "not_available"
        _log.error(cmd_error.decode('utf-8').rstrip())

    else:
        # Convert bytes to text and remove \n
        try:
            cmd_reply = cmd_reply.decode('utf-8').rstrip()
        except UnicodeDecodeError:
            _log.error("Failed to decode to utf-8.")

    return cmd_reply, cmd.returncode


def get_host_ips():
    """Get external facing system IP from default route, do not rely on hostname.

    Returns:
      A string containing the ip
    """
    _, _, ip_list = socket.gethostbyaddr(socket.getfqdn())
    ip_address = ','.join(ip_list)
    return ip_address


def bench_versions(conf):
    """Extract benchmark version information.

    Args:
      conf: Full configutaion dict

    Returns:
      A dict with a mapping of benchmark and version.
    """

    bench_versions = {}

    for bench in conf['global']['benchmarks']:

        if bench == 'hs06':
            bench_versions[bench] = conf['hepspec06']['image'].split(":")[-1]

        elif bench == 'db12':
            bench_versions[bench] = "v0.1"

        elif bench == 'spec2017':
            bench_versions[bench] = conf['spec2017']['image'].split(":")[-1]

        elif bench == 'hepscore':
            bench_versions[bench] = conf['hepscore']['version']

        else:
            bench_versions[bench] = "not_available"
            _log.warning("No version found for benchmark: %s", bench)

    _log.debug("Benchmark versions found: %s", bench_versions)
    return bench_versions


def prepare_metadata(full_conf, extra):
    """Construct a json with cli inputs and extra fields.

    Args:
      cli_inputs: Arguments that were passed directly with cli
      extra:  Extra dict with fields to include

    Returns:
      A dict containing hardware metadata, tags, flags & extra fields
    """
    # Create output metadata

    params = full_conf['global']

    result = {'host': {}, 'suite': {}}
    result.update({
        '_id'           : str(uuid.uuid4()),
        '_timestamp'    : extra['start_time'],
        '_timestamp_end': extra['end_time'],
        'json_version'  : __version__
    })

    result['host'].update({
        'hostname': socket.gethostname(),
        'ip'      : get_host_ips(),
    })

    for i in ['tags']:
        try:
            result['host'].update({"{}".format(i): params[i]})
        except:
            result['host'].update({"{}".format(i): "not_defined"})

    # Hep-benchmark-suite flags
    flags = {
        'mp_num'  : params['mp_num'],
        'run_mode': params['mode'],
    }

    result['suite'].update({
        'version'          : __version__,
        'flags'            : flags,
        'benchmark_version': bench_versions(full_conf)
    })

    # Collect Software and Hardware metadata from hwmetadata plugin
    hw_data = Extractor(params)

    result['host'].update({
        'SW': hw_data.collect_sw(),
        'HW': hw_data.collect_hw(),
    })

    return result


def print_results(results):
    """Print the results in a human-readable format.

    Args:
      results: A dict containing the results['profiles']
    """
    print("\n\n=========================================================")
    print("BENCHMARK RESULTS FOR {}".format(results['host']['hostname']))
    print("=========================================================")
    print("Suite start: {}".format(results['_timestamp']))
    print("Suite end:   {}".format(results['_timestamp_end']))
    print("Machine CPU Model: {}".format(results['host']['HW']['CPU']['CPU_Model']))

    data = results['profiles']

    def parse_hepscore(data):
        # Attempt to use the new format of hepscore reporting
        # can be dropped in the future once metadata is standard
        try:
            result = round(data['report']['score'], 2)
        except KeyError:
            result = round(data['score'], 2)
        return "HEPSCORE Benchmark = {} over benchmarks {}".format(result, data['benchmarks'].keys())

    bmk_print_action = {
        "DB12"    : lambda x: "DIRAC Benchmark = %.3f (%s)" % (float(data[x]['value']), data[x]['unit']),
        "hs06_32" : lambda x: "HS06 32 bit Benchmark = {}".format(data[x]['score']),
        "hs06_64" : lambda x: "HS06 64 bit Benchmark = {}".format(data[x]['score']),
        "hs06"    : lambda x: "HS06 Benchmark = {}".format(data[x]['score']),
        "spec2017": lambda x: "SPEC2017 64 bit Benchmark = {}".format(data[x]['score']),
        "hepscore": lambda x: parse_hepscore(data[x]),
    }

    for bmk in sorted(results['profiles']):
        # This try covers two cases: that the expected printout fails
        # or that the item is not know in the print_action
        try:
            print(bmk_print_action[bmk](bmk))
        except:
            print("{} : {}".format(bmk, results['profiles'][bmk]))


def print_results_from_file(json_file):
    """Print the results from a json file.

    Args:
      json_file: A json file with results
    """
    with open(json_file, 'r') as jfile:
        print_results(json.loads(jfile.read()))