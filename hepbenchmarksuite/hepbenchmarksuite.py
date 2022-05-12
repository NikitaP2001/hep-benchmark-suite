"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import os
import json
import logging
import time
import shutil

from hepbenchmarksuite import db12
from hepbenchmarksuite import utils
from hepbenchmarksuite import benchmarks
from hepbenchmarksuite.exceptions import PreFlightError
from hepbenchmarksuite.exceptions import BenchmarkFailure
from hepbenchmarksuite.exceptions import BenchmarkFullFailure
from hepbenchmarksuite.plugins.send_queue import is_key_password_protected

_log = logging.getLogger(__name__)


class HepBenchmarkSuite:
    """********************************************************
                  *** HEP-BENCHMARK-SUITE ***
     *********************************************************"""
    # Location of result files
    RESULT_FILES = {
        'hs06'    : 'HS06/hs06_result.json',
        'spec2017': 'SPEC2017/spec2017_result.json',
        'hepscore': 'HEPSCORE/hepscore_result.json',
        'db12'    : 'db12_result.json',
    }

    # Required disk space (in GB) for all benchmarks
    DISK_THRESHOLD = 20.0

    def __init__(self, config=None):
        """Initialize setup"""
        self._bench_queue        = config['global']['benchmarks'].copy()
        self.selected_benchmarks = config['global']['benchmarks'].copy()
        self._config             = config['global']
        self._config_full        = config
        self._extra              = {}
        self._result             = {}
        self.failures            = []

    def start(self):
        """Entrypoint for suite."""
        _log.info("Starting HEP Benchmark Suite")

        self._extra['start_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        if self.preflight():
            _log.info("Pre-flight checks passed successfully.")
            self.run()
        else:
            _log.error("Pre-flight checks failed.")
            raise PreFlightError

    def preflight(self):
        """Perform pre-flight checks."""

        _log.info("Running pre-flight checks")
        checks = []

        _log.info(" - Checking if selected run mode exists...")

        # Avoid executing commands if they are not valid run modes.
        # This avoids injections through the configuration file.
        if self._config['mode'] in ('docker', 'singularity'):

            # Search if run mode is installed
            system_runmode = shutil.which(self._config['mode'])

            if system_runmode is not None:
                _log.info("   - %s executable found: %s.", self._config['mode'], system_runmode)

                if self._config['mode'] == 'docker':
                    version, _ = utils.exec_cmd("docker version --format '{{.Server.Version}}'")

                elif self._config['mode'] == 'singularity':
                    version, _ = utils.exec_cmd('singularity version')

                _log.info("   - %s version: %s.", self._config['mode'], version)

            else:
                _log.error("   - %s is not installed in the system.", self._config['mode'])
                checks.append(1)

        else:
            _log.error("Invalid run mode specified: %s.", self._config['mode'])
            checks.append(1)

        _log.info(" - Checking provided work dirs exist...")
        os.makedirs(self._config['rundir'], exist_ok=True)

        if 'hs06' in self.selected_benchmarks:
            os.makedirs(self._config_full['hepspec06']['hepspec_volume'], exist_ok=True)

        if 'spec2017' in self.selected_benchmarks:
            os.makedirs(self._config_full['spec2017']['hepspec_volume'], exist_ok=True)

        if 'hepscore' in self.selected_benchmarks:
            os.makedirs(os.path.join(self._config['rundir'], "HEPSCORE"), exist_ok=True)

        _log.info(" - Checking for a valid configuration...")
        for bench in self.selected_benchmarks:
            if bench in ('hs06', 'spec2017'):
                checks.append(benchmarks.validate_spec(self._config_full, bench))

        _log.info(" - Checking if rundir has enough space...")
        disk_stats    = shutil.disk_usage(self._config['rundir'])
        disk_space_gb = round(disk_stats.free * (10 ** -9), 2)

        _log.debug("Calculated disk space: %s GB", disk_space_gb)
        if disk_space_gb <= self.DISK_THRESHOLD and not (len(self.selected_benchmarks) == 1 and 'db12' in self.selected_benchmarks):
            _log.error("Not enough disk space on %s, free: %s GB, required: %s GB", self._config['rundir'], disk_space_gb, self.DISK_THRESHOLD)

            # Flag for a failed check
            checks.append(1)

        # Checking if private key for AMQ is password protected
        if self._config.get('publish') and 'activemq' in self._config_full:
            _log.info(" - Checking AMQ configuration for key protection")
            amq_cfg = self._config_full['activemq']
            if "key" in amq_cfg and is_key_password_protected(amq_cfg['key']):
                _log.warning("The private key is password protected. After the configured benchmark(s) have run, you "
                             "will need to input the password or the execution will stall")
                _log.warning("Otherwise, you may set the publish variable to false and send the results afterwards "
                             "using bmksend, which is included in the suite")

        # Check if any pre-flight check failed
        if any(checks):
            return False
        else:
            return True

    def run(self):
        """Run the benchmark at the head of _bench_queue and recurse"""

        # Check if there are still benchmarks to run
        if len(self._bench_queue) == 0:
            self._extra['end_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            self.cleanup()

        else:
            _log.info("Benchmarks left to run: %s", self._bench_queue)
            bench2run = self._bench_queue.pop(0)
            _log.info("Running benchmark: %s", bench2run)

            if bench2run == 'db12':
                # TO FIX returns a dict{'DB12':{ 'value': float(), 'unit': string() }}
                returncode = db12.run_db12(rundir=self._config['rundir'], cpu_num=2)

                if not returncode['DB12']['value']:
                    self.failures.append(bench2run)

            elif bench2run == 'hepscore':
                # Prepare hepscore
                if benchmarks.prep_hepscore(self._config_full) == 0:
                    # Run hepscore
                    returncode = benchmarks.run_hepscore(self._config_full)
                    if returncode < 0:
                        self.failures.append(bench2run)
                else:
                    _log.error("Skipping hepscore due to failed installation.")

            elif bench2run in ('hs06', 'spec2017'):
                returncode = benchmarks.run_hepspec(conf=self._config_full, bench=bench2run)
                if returncode > 0:
                    self.failures.append(bench2run)
            _log.info("Completed %s with return code %s", bench2run, returncode)
            # recursive call to run() with check_lock
            self.check_lock()

    def check_lock(self):
        """Check benchmark locks."""
        # TODO: Check lock files
        # loop until lock is released from benchmark
        # print(os.path.exists("bench.lock"))
        # Release lock and resume benchmarks
        self.run()

    def cleanup(self):
        """Run the cleanup phase - collect the results from each benchmark"""

        # compile metadata
        self._result = utils.prepare_metadata(self._config_full, self._extra)
        self._result.update({'profiles': {}})

        # Get results from each benchmark
        for bench in self.selected_benchmarks:
            try:
                result_path = os.path.join(self._config['rundir'], self.RESULT_FILES[bench])

                with open(result_path, "r") as result_file:
                    _log.info("Reading result file: %s", result_path)

                    if bench == "hepscore":
                        self._result['profiles']['hepscore'] = json.loads(result_file.read())
                    else:
                        self._result['profiles'].update(json.loads(result_file.read()))

            except Exception as err:
                _log.warning('Skipping %s because of %s', bench, err)

        # Save complete json report
        with open(os.path.join(self._config['rundir'], "bmkrun_report.json"), 'w') as fout:
            fout.write(json.dumps(self._result))

        # Check for workload errors
        if len(self.failures) == len(self.selected_benchmarks):
            _log.error('All benchmarks failed!')
            raise BenchmarkFullFailure

        elif len(self.failures) > 0:
            _log.error("%s Failed. Please check the logs.", self.failures)
            raise BenchmarkFailure

        else:
            _log.info("Successfully completed all requested benchmarks")
