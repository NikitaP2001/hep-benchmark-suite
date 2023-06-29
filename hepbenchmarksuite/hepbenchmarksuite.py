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

from hepbenchmarksuite import db12
from hepbenchmarksuite import utils
from hepbenchmarksuite import benchmarks
from hepbenchmarksuite.preflight import Preflight
from hepbenchmarksuite.exceptions import PreFlightError
from hepbenchmarksuite.exceptions import BenchmarkFailure
from hepbenchmarksuite.exceptions import BenchmarkFullFailure

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

    def __init__(self, config=None):
        """Initialize setup"""
        self._bench_queue        = config['global']['benchmarks'].copy()
        self.selected_benchmarks = config['global']['benchmarks'].copy()
        self._config             = config['global']
        self._config_full        = config
        self._extra              = {}
        self._result             = {}
        self.failures            = []
        self.preflight           = Preflight(config)

    def start(self):
        """Entrypoint for suite."""
        _log.info("Starting HEP Benchmark Suite")

        self._extra['start_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        if self.preflight.check():
            _log.info("Pre-flight checks passed successfully.")
            self.run()
        else:
            _log.error("Pre-flight checks failed.")
            raise PreFlightError

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
                returncode = 0
                result = db12.run_db12(rundir = self._config['rundir'],
                                       cpu_num = self._config_full['global']['ncores'])

                if not result['DB12']['value']:
                    self.failures.append(bench2run)
                    returncode = 1

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
