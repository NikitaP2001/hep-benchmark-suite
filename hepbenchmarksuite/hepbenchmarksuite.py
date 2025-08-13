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
import math

import importlib_resources

from hepbenchmarksuite import benchmarks
from hepbenchmarksuite import db12
from hepbenchmarksuite import utils
from hepbenchmarksuite.exceptions import BenchmarkFailure
from hepbenchmarksuite.exceptions import BenchmarkFullFailure
from hepbenchmarksuite.exceptions import PreFlightError
from hepbenchmarksuite.plugins.construction.config_builder import ConfigPluginBuilder
from hepbenchmarksuite.plugins.construction.dynamic_metadata_provider import DynamicPluginMetadataProvider
from hepbenchmarksuite.plugins.extractor import Extractor
from hepbenchmarksuite.plugins.runner import PluginRunner
from hepbenchmarksuite.preflight import Preflight
from hepbenchmarksuite.__version__ import __version__

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

        _log.info(f"Initializing HEP Benchmark Suite {__version__}")

        self.preflight = Preflight(config)

        plugin_config = config.get('plugins', {})
        ref = importlib_resources.files('hepbenchmarksuite.plugins.registry')
        with importlib_resources.as_file(ref) as plugin_registry_path:
            self.plugin_metadata_provider = DynamicPluginMetadataProvider(plugin_registry_path)
        plugin_builder = ConfigPluginBuilder(plugin_config, self.plugin_metadata_provider)
        self.plugin_runner = PluginRunner(plugin_builder)

    def start(self):
        """Entrypoint for suite."""
        _log.info("Starting HEP Benchmark Suite")

        self._extra['start_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        # Collecting Metadata at the start to prevent failures after the full run [BMK-1464]
        extractor = Extractor(self._config)
        self._result = utils.prepare_metadata(self._config_full, self._extra, extractor)

        if self.preflight.check():
            _log.info("Pre-flight checks passed successfully.")
            self.plugin_runner.initialize()
            self._run_plugins_synchronously('pre', self._config.get('pre-stage-duration', 0))
            self.run()
            self._extra['end_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            self._run_plugins_synchronously('post', self._config.get('post-stage-duration', 0))
            self.finalize()
        else:
            _log.error("Pre-flight checks failed.")
            raise PreFlightError

    def _run_plugins_synchronously(self, key, duration_mins: float):
        """Run a plugin synchronously for stage 'key'."""
        _log.info("Collecting plugins for stage '%s'", key)
        self.plugin_runner.start_plugins()

        _log.info("Idling system for %.1f minutes.", duration_mins)
        duration_secs = duration_mins * 60
        time.sleep(duration_secs)

        self.plugin_runner.stop_plugins(key)

    def run(self):
        """Run benchmarks sequentially."""
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
        """
        Execute the specified benchmark using the suite's configuration.

        Args:
            bench2run (str): Name of the benchmark to execute, one of: 'db12', 'hepscore', 'hs06', 'spec2017'.

        Returns:
            int: 0 if successful, 1 otherwise.

        Raises:
            Exception: If a benchmark crashes, the exception is logged to error and the return code is set to 1.
        """
        return_code = 1
        try:
            if bench2run == 'db12':
                result = db12.run_db12(rundir=self._config['rundir'],
                                       cpu_num=self._config_full['global']['ncores'])
                if result['DB12']['value']:
                    return_code = 0
            elif bench2run == 'hepscore':
                if benchmarks.prep_hepscore(self._config_full) == 0:
                    return_code = benchmarks.run_hepscore(self._config_full)
                else:
                    _log.error("Skipping hepscore due to failed installation.")
            elif bench2run in ('hs06', 'spec2017'):
                return_code = benchmarks.run_hepspec(conf=self._config_full, bench=bench2run)
        except Exception as e:
            _log.error(f"Benchmark {bench2run} crashed: {e}")

        if return_code != 0:
            self.failures.append(bench2run)

        return return_code

    def finalize(self):
        """Finalize the benchmark execution - collect results, save reports, and check for errors"""
        self._compile_benchmark_results()
        self._save_complete_report()
        self._check_for_workload_errors()

    def _compile_benchmark_results(self):
        self._result.update({'_timestamp_end': self._extra['end_time']})  # Update metadata: _timestamp_end [BMK-1464]
        self._result.update({'plugins': self.plugin_runner.get_results()})
        self._result.update({'profiles': {}})

        # Get results from each benchmark
        for bench in self.selected_benchmarks:
            try:
                result_path = os.path.join(self._config['rundir'], self.RESULT_FILES[bench])

                with open(result_path, "r", encoding='utf-8') as result_file:
                    _log.info("Reading result file: %s", result_path)

                    if bench == "hepscore":
                        self._result['profiles']['hepscore'] = json.loads(result_file.read())
                    else:
                        self._result['profiles'].update(json.loads(result_file.read()))

            except Exception as err:  # pylint: disable=broad-except
                _log.warning('Skipping %s because of %s', bench, err)

    def _save_complete_report(self):

        def nan2None(obj):
            if isinstance(obj, dict):
                return {k:nan2None(v) for k,v in obj.items()}
            elif isinstance(obj, list):
                return [nan2None(v) for v in obj]
            elif isinstance(obj, float) and math.isnan(obj):
                return None
            return obj

        class NanConverter(json.JSONEncoder):
            def encode(self, obj, *args, **kwargs):
                return super().encode(nan2None(obj), *args, **kwargs)

        report_file_path = os.path.join(self._config['rundir'], "bmkrun_report.json")
        with open(report_file_path, 'w', encoding='utf-8') as output_file:
            dump = json.dumps(self._result, cls=NanConverter)
            _log.info("Saving final report: %s", report_file_path)
            _log.debug("Report: %s", dump)
            output_file.write(dump)

    def _check_for_workload_errors(self):
        if len(self.failures) == len(self.selected_benchmarks):
            _log.error('All benchmarks failed!')
            raise BenchmarkFullFailure
        if len(self.failures) > 0:
            _log.error("%s Failed. Please check the logs.", self.failures)
            raise BenchmarkFailure
        _log.info("Successfully completed all requested benchmarks")
