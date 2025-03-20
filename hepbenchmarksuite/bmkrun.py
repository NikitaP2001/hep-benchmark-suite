#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
################################################################################
"""

import argparse
import datetime
import logging
import sys
import socket
import os
import textwrap
import time
import yaml

from hepbenchmarksuite import benchmarks
from hepbenchmarksuite.hepbenchmarksuite import HepBenchmarkSuite

from hepbenchmarksuite import utils
from hepbenchmarksuite import config

from hepbenchmarksuite.exceptions import PreFlightError
from hepbenchmarksuite.exceptions import BenchmarkFailure
from hepbenchmarksuite.exceptions import BenchmarkFullFailure

from hepbenchmarksuite.plugins import send_queue
from hepbenchmarksuite.plugins import send_opensearch
from hepbenchmarksuite.__version__ import __version__


class Color:
    """ Console colors. """
    CYAN      = '\033[96m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    END       = '\033[0m'
    WHITE     = "\033[97m"


class ExitStatus:
    """ bmkrun exit status """
    NO_CONFIG_FILE = 1
    FILE_NOT_FOUND = 2
    MISSING_BENCHMARK = 3
    INVALID_BENCHMARK = 4
    INVALID_CPU_NUMBER = 5
    SUITE_FAILS = 6


# Define logger as a global variable
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set the default log level


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='bmkrun',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''
        -----------------------------------------------
        High Energy Physics Benchmark Suite
        -----------------------------------------------
        This utility orchestrates several benchmarks.

        Author: Benchmarking Working Group
        Contact: https://wlcg-discourse.web.cern.ch/c/hep-benchmarks
        '''), epilog=textwrap.dedent('''
        -----------------------------------------------
        '''),
    )

    # Arguments
    parser.add_argument("-b", "--benchmarks",
                        nargs='+',
                        help="List of benchmarks.",
                        default=None)

    parser.add_argument("-c", "--config",
                        nargs='?',
                        type=str,
                        help="REQUIRED - Configuration file to use (yaml format). Accepts '-c default'.",
                        default=None)

    parser.add_argument("-d", "--rundir",
                        nargs='?',
                        help="Directory where benchmarks will be run.",
                        default=None)

    parser.add_argument("-e", "--export",
                        action='store_true',
                        help="Export all json and log files from rundir and compresses them.",
                        default=None)

    parser.add_argument("-m", "--mode",
                        choices=['singularity', 'docker'],
                        nargs='?',
                        help="Run benchmarks in singularity or docker containers.",
                        default=None)

    parser.add_argument("-n", "--ncores",
                        nargs='?',
                        type=int,
                        help="Number of cpus to run the benchmarks.",
                        default=None)

    parser.add_argument("-p", "--publish",
                        action='store_true',
                        help="Enable reporting via AMQ credentials in YAML file.",
                        default=None)

    parser.add_argument("-s", "--show",
                        action='store_true',
                        help="Show running config and exit.",
                        default=None)

    parser.add_argument("-t", "--tags",
                        action='store_true',
                        help="Enable reading of user tags from ENV variables (BMKSUITE_TAG_{TAG}). Tags specified in configuration file are ignored.",
                        default=None)

    parser.add_argument("-V", "--extra_volumes",
                        nargs='+',
                        help="List of additional volumes to mount on the container.",
                        default=None)

    parser.add_argument("-v", "--verbose",
                        action='store_true',
                        help="Enable verbose mode. Display debug messages.",
                        default=None)

    parser.add_argument('--version',
                        action='version',
                        version='{version}'.format(version=__version__))

    return parser

def load_configuration(args):
    '''Select the config file to load
    load default configuration shipped with hep-benchmark-suite
    '''

    if args['config'] == "default":
        config_file = os.path.join(config.__path__[0], 'benchmarks.yml')
    elif args['config'] is None:
    # No configuration file was provided
        parse_arguments().print_help()
        print("{}No configuration file specified.{}".format(Color.RED,Color.END))
        print("{}Please specify a configuration or run with the default: bmkrun -c default {}".format(Color.RED,Color.END))
        sys.exit(ExitStatus.NO_CONFIG_FILE)
    else:
        config_file = args['config']

    # Load configuration file
    try:
        with open(config_file, encoding='utf-8') as yam:
            config_dict =  yaml.full_load(yam)
            print("# The following configuration was loaded: {}".format(config_file))
            return config_dict
    except FileNotFoundError:
        print("{0}Failed to load configuration file: {1} {2}".format(Color.RED, config_file, Color.END))
        sys.exit(ExitStatus.FILE_NOT_FOUND)

def check_and_override_config(active_config, args):
    """Check for CLI overrides and update the active configuration."""
    del args['config']

    # Get non-None cli arguments to override config file
    non_empty = {k: v for k, v in args.items() if v is not None}

    if 'global' not in active_config:
        print("{}No global section found in configuration.{}".format(Color.RED,Color.END))
        print("Please refer to https://gitlab.cern.ch/hep-benchmarks/hep-benchmark-suite\
            /-/blob/{}/hepbenchmarksuite/config/benchmarks.yml for a working example \
            for your version of the suite ({})".format(__version__, __version__))
        sys.exit(ExitStatus.NO_CONFIG_FILE)

    # Populate active config with cli override
    for i in non_empty.keys():
        if i == 'tags':
            # Update tags with json format
            active_config['global']['tags'] = utils.get_tags_env()
        else:
            active_config['global'][i] = non_empty[i]

    # Check if user provided a benchmark
    if 'benchmarks' not in active_config['global'] or active_config['global']['benchmarks'] is None:
        parse_arguments().print_help()
        print("{}No benchmarks were selected. {}".format(Color.YELLOW, Color.END))
        sys.exit(ExitStatus.MISSING_BENCHMARK)

    # Check if user provided valid benchmark
    AVAILABLE_BENCHMARKS = ("db12", "hepscore", "spec2017", "hs06")

    for bench in active_config['global']['benchmarks']:
        if bench not in AVAILABLE_BENCHMARKS:
            print('{}Benchmark "{}" is not a valid benchmark.{}'.format(Color.RED, bench, Color.END))
            print('Please select one of the following benchmarks:\n- {}'.format(
                '\n- '.join(AVAILABLE_BENCHMARKS)))
            sys.exit(ExitStatus.INVALID_BENCHMARK)

    # Check if cpu count in config is integer
    if 'ncores' in active_config['global'].keys():
        if not isinstance(active_config['global']['ncores'], int):
            print("{}CPU number (ncores) is not an integer.{}".format(Color.RED, Color.END))
            sys.exit(ExitStatus.INVALID_CPU_NUMBER)
        elif (active_config['global']['ncores'] is None or
                int(active_config['global']['ncores']) > os.cpu_count()):
                active_config['global']['ncores'] = os.cpu_count()
    else:
        #ncores is not defined in global, adding it
        # use all CPUs found if invalid parameter provided
        active_config['global']['ncores'] = os.cpu_count()


    # Set default duration of pre- and post-stage
    active_config['global'].setdefault('pre-stage-duration', 0)
    active_config['global'].setdefault('post-stage-duration', 0)

    if len(non_empty):
        print("# The configuration was overridden by the following CLI args: {}".format(non_empty))

    # Print running configuration and exit
    if args['show']:
        print(yaml.dump(active_config))
        sys.exit(0)


def create_run_directory(active_config):
    """Create run directories based on configuration."""
    active_config['global']['parent_dir'] = active_config['global']['rundir']
    os.makedirs(active_config['global']['parent_dir'], exist_ok=True)
    active_config['global']['rundir'] = os.path.join(
        active_config['global']['rundir'],
        'run_{}'.format(time.strftime('%Y-%m-%d_%H%M', time.gmtime())))
    os.makedirs(active_config['global']['rundir'], exist_ok=True)


def configure_logging(active_config, args):
    """Configure logging based on the configuration."""
    if args['verbose']:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    global logger
    # Enable logging
    logger.setLevel(log_level)

    # Log format
    log_formatter = logging.Formatter('%(asctime)s, %(name)s:%(funcName)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Handler to write logs to stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(log_level)

    # Handler to write logs to file
    global LOG_PATH
    LOG_PATH = os.path.join(active_config['global']['rundir'], 'hep-benchmark-suite.log')
    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(log_level)

    # Select loggers
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)


def save_running_config(active_config):
    """Save the running configuration."""
    with open(os.path.join(active_config['global']['rundir'], 'run_config.yaml'), 'w') as conf_file:
        yaml.dump(active_config, conf_file)

def run_benchmarks(active_config):
    """Run benchmarks based on the provided configuration."""

    logger.debug("Active configuration in use: %s", active_config)
    suite = HepBenchmarkSuite(config=active_config)
    try:
        suite.start()
    except PreFlightError:
        logger.error("HEP-Benchmark Suite failed.")
        sys.exit(ExitStatus.SUITE_FAILS)
    except (BenchmarkFailure, BenchmarkFullFailure):
        logger.warning("HEP-Benchmark Suite ran with failed benchmarks. Please be aware of the results.")

def export_results(args, active_config):
    """Export logs and results."""
    # format of export: dirname_hostname_datetime.tar.gz
    if args['export']:
        utils.export(active_config['global']['rundir'], '{}_{}_{}.tar.gz'.format(
            os.path.split(active_config['global']['rundir'])[-1],
            socket.gethostname(),
            datetime.datetime.now().strftime("%Y-%m-%d_%H%M")))

def display_results(report_path):
    """Display benchmarking results."""
    utils.print_results_from_file(report_path)
    print("\n{}Full results can be found in {} {}".format(Color.CYAN, report_path, Color.END))
    print("{}Full run log can can be found in {} {}".format(Color.CYAN, LOG_PATH, Color.END))

def publish_results(active_config, report_path):
    """Publish results if needed."""    
    # Publish to AMQ broker if provided
    if active_config['global'].get('publish'):
        try:
            if active_config.get("activemq", False):
                send_queue.send_message(report_path, active_config['activemq'])
            elif active_config.get("opensearch", False):
                send_opensearch.send_message(report_path, active_config['opensearch'])
            else:
                logger.error("configuration was set to publish but no publisher was configured.")
        except Exception as err:
            logger.error("Something went wrong attempting to report via AMQ/OpenSearch.")
            logger.error("Results may not have been correctly transmitted.")
            logger.exception(err)

def main():
    """Main function."""
    args = vars(parse_arguments().parse_args())
    active_config = load_configuration(args)
    
    check_and_override_config(active_config, args)
    create_run_directory(active_config)
    configure_logging(active_config, args)
    save_running_config(active_config)
    run_benchmarks(active_config)
    
    report_path = os.path.join(active_config['global']['rundir'], "bmkrun_report.json")
    export_results(args, active_config)
    display_results(report_path)
    publish_results(active_config, report_path)


if __name__ == "__main__":
    main()
