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
import time

import pkg_resources

from hepbenchmarksuite import benchmarks
from hepbenchmarksuite import db12
from hepbenchmarksuite import utils
from hepbenchmarksuite.exceptions import BenchmarkFailure
from hepbenchmarksuite.exceptions import BenchmarkFullFailure
from hepbenchmarksuite.exceptions import PreFlightError
from hepbenchmarksuite.plugins.construction.config_builder import ConfigPluginBuilder
from hepbenchmarksuite.plugins.construction.dynamic_metadata_provider import DynamicPluginMetadataProvider
from hepbenchmarksuite.plugins.runner import PluginRunner
from hepbenchmarksuite.preflight import Preflight

_log = logging.getLogger(__name__)


class HepBenchmarkSuite:
    """********************************************************
                  *** HEP-BENCHMARK-SUITE ***
     *********************************************************"""
    # Location of result files
    RESULT_FILES = {
        'hs06': 'HS06/hs06_result.json',
        'spec2017': 'SPEC2017/spec2017_result.json',
        'hepscore': 'HEPSCORE/hepscore_result.json',
        'db12': 'db12_result.json',
    }

    def __init__(self, config=None):
        """Initialize setup"""
        self._bench_queue = config['global']['benchmarks'].copy()
        self.selected_benchmarks = config['global']['benchmarks'].copy()
        self._config = config['global']
        self._config_full = config
        self._extra = {}
        self._result = {}
        self.failures = []
        self.preflight = Preflight(config)

        plugin_config = config.get('plugins', {})
        plugin_registry_path = pkg_resources.resource_filename('hepbenchmarksuite.plugins.registry', '')
        self.plugin_metadata_provider = DynamicPluginMetadataProvider(plugin_registry_path)
        self.plugin_metadata_provider.initialize()
        plugin_builder = ConfigPluginBuilder(plugin_config, self.plugin_metadata_provider)
        self.plugin_runner = PluginRunner(plugin_builder)

    def start(self):
        """Entrypoint for suite."""
        _log.info("Starting HEP Benchmark Suite")

        self._extra['start_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        if self.preflight.check():
            _log.info("Pre-flight checks passed successfully.")
            self.plugins_sync_run('pre')
            self.run()
            self._extra['end_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            self.plugins_sync_run('post')
            self.cleanup()
        else:
            _log.error("Pre-flight checks failed.")
            raise PreFlightError

    def plugins_sync_run(self, key):
        _log.info(f"Running plugins synchronously: {key}")
        self.plugin_runner.start_plugins()
        time.sleep(0)  # TODO - make this configurable
        self.plugin_runner.stop_plugins(key)

    def run(self):
        """Runs benchmarks sequentially."""
        for bench2run in self._bench_queue:
            _log.info("Benchmarks left to run: %s", self._bench_queue)
            _log.info("Running benchmark: %s", bench2run)

            self.plugin_runner.start_plugins()
            try:
                return_code = self._run_benchmark(bench2run)
            finally:
                if self.plugin_runner.are_plugins_running():
                    self.plugin_runner.stop_plugins(bench2run)
            _log.info("Completed %s with return code %s", bench2run, return_code)

    def _run_benchmark(self, bench2run):
        if bench2run == 'db12':
            return_code = 0
            result = db12.run_db12(rundir = self._config['rundir'],
                                   cpu_num = self._config_full['global']['ncores'])

            if not result['DB12']['value']:
                self.failures.append(bench2run)
                return_code = 1

        elif bench2run == 'hepscore':
            # Prepare hepscore
            if benchmarks.prep_hepscore(self._config_full) == 0:
                # Run hepscore
                return_code = benchmarks.run_hepscore(self._config_full)
                if return_code < 0:
                    self.failures.append(bench2run)
            else:
                _log.error("Skipping hepscore due to failed installation.")

        elif bench2run in ('hs06', 'spec2017'):
            return_code = benchmarks.run_hepspec(conf=self._config_full, bench=bench2run)
            if return_code > 0:
                self.failures.append(bench2run)

        return return_code

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
        self._result.update({'plugins': self.plugin_runner.get_results()})
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
        report_file_path = os.path.join(self._config['rundir'], "bmkrun_report.json")
        with open(report_file_path, 'w') as fout:
            dump = json.dumps(self._result)
            _log.info("Saving final report: %s", report_file_path)
            _log.debug("Report: %s", dump)
            fout.write(dump)

        # Check for workload errors
        if len(self.failures) == len(self.selected_benchmarks):
            _log.error('All benchmarks failed!')
            raise BenchmarkFullFailure

        elif len(self.failures) > 0:
            _log.error("%s Failed. Please check the logs.", self.failures)
            raise BenchmarkFailure

        else:
            _log.info("Successfully completed all requested benchmarks")
