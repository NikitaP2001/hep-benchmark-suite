#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import copy
import os
import shutil
import time
import unittest
from unittest.mock import patch, mock_open

import yaml

from hepbenchmarksuite import benchmarks
from hepbenchmarksuite.exceptions import PreFlightError, BenchmarkFailure, BenchmarkFullFailure
from hepbenchmarksuite.hepbenchmarksuite import HepBenchmarkSuite
from hepbenchmarksuite.preflight import Preflight


class TestSuite(unittest.TestCase):
    """ Test the HepBenchmarkSuite """

    @classmethod
    def setUpClass(cls):
        """ Load CI configuration """

        with open("tests/ci/benchmarks.yml", 'r') as cfg_file:
            cls.config_file = yaml.full_load(cfg_file)
            cls.config_file['global']['parent_dir'] = '.'

    def _get_config(self):
        return copy.deepcopy(self.config_file)

    def test_preflight_fail(self):
        """ Test the suite preflight failures. """

        sample_config = self._get_config()

        # Force a failure of missing singularity/docker
        shutil.which = lambda x: None

        suite = HepBenchmarkSuite(sample_config)

        # The suite should raise an exception PreFlightError
        with self.assertLogs('hepbenchmarksuite.hepbenchmarksuite', level='INFO') as log:
            with self.assertRaises(PreFlightError):
                suite.start()
            self.assertIn('ERROR:hepbenchmarksuite.hepbenchmarksuite:'
                          'Pre-flight checks failed.', " ".join(log.output))

        # Preflight check should not pass
        with self.assertLogs('hepbenchmarksuite.preflight', level='INFO') as log:
            assert suite.preflight.check() == False
            output = " ".join(log.output)

            for message in ['ERROR', 'hepbenchmarksuite.preflight',
                            'singularity is not installed in the system']:
                self.assertIn(message, output)

    @patch.object(Preflight, 'check', return_code=1)
    @patch.object(HepBenchmarkSuite, 'finalize', return_code=0)
    def test_suite_run(self, mock_preflight, mock_finalize):
        """ Test the benchmark suite main run.
         Mocking to simulate the following conditions:
         - Assumes that preflight were successfull.
         - Avoids running finalize stage.
        """

        sample_config = self._get_config()

        # To avoid running the benchmarks.
        # Asssumes it was successfull.
        benchmarks.run_hepspec = lambda conf, bench: 0
        benchmarks.prep_hepscore = lambda conf: 0
        benchmarks.run_hepscore = lambda conf: 1

        sample_config['global']['benchmarks'] = ['hs06', 'spec2017', 'hepscore']

        suite = HepBenchmarkSuite(sample_config)

        # Suite should print successful message after each benchmark completion
        with self.assertLogs('hepbenchmarksuite.hepbenchmarksuite', level='INFO') as log:
            suite.start()
            self.assertIn('INFO:hepbenchmarksuite.hepbenchmarksuite:'
                          'Completed hs06 with return code 0',
                          " ".join(log.output))
            self.assertIn('INFO:hepbenchmarksuite.hepbenchmarksuite:'
                          'Completed spec2017 with return code 0',
                          " ".join(log.output))
            self.assertIn('INFO:hepbenchmarksuite.hepbenchmarksuite:'
                          'Completed hepscore with return code 1',
                          " ".join(log.output))

    @patch('builtins.open', new_callable=mock_open, read_data='{"data":1}')
    def test_finalize(self, mock_file):
        """ Test if suite finalize raises exceptions on failed benchmarks. """
        sample_config = self._get_config()
        sample_config['global']['ncores'] = 2

        suite = HepBenchmarkSuite(sample_config)

        suite._extra['start_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        suite._extra['end_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        os.makedirs(sample_config['global']['rundir'], exist_ok=True)

        # Test success
        with self.assertLogs('hepbenchmarksuite.hepbenchmarksuite', level='INFO') as finalizelog:
            suite.finalize()

            self.assertIn('INFO:hepbenchmarksuite.hepbenchmarksuite:'
                          'Successfully completed all requested benchmarks',
                          finalizelog.output)

        # Test when one benchmark fails with multiple benchmarks selected
        suite.failures = [1]
        suite.selected_benchmarks = ['db12', 'hepscore']
        with self.assertRaises(BenchmarkFailure):
            suite.finalize()

        # Test when all selected benchmarks fail
        suite.selected_benchmarks = ['db12']
        with self.assertRaises(BenchmarkFullFailure):
            suite.finalize()

        # Test array of failures, but reportable success
        suite.failures = [1, 2]
        suite.selected_benchmarks = ['db12', 'hepscore', 'hs06_32']
        with self.assertRaises(BenchmarkFailure):
            suite.finalize()

    @patch('time.sleep', return_value=None)
    @patch.object(Preflight, 'check', return_code=0)
    @patch.object(HepBenchmarkSuite, 'run', return_code=None)
    @patch.object(HepBenchmarkSuite, 'finalize', return_code=0)
    def test_stage_duration_config(self, mock_sleep, mock_preflight, mock_run, mock_finalize):
        # Load default config
        sample_config = self._get_config()
        # Set custom duration
        sample_config['global']['pre-stage-duration'] = 1
        sample_config['global']['post-stage-duration'] = 2

        suite = HepBenchmarkSuite(sample_config)

        with self.assertLogs('hepbenchmarksuite.hepbenchmarksuite', level='DEBUG') as log:
            suite.start()

            self.assertIn("DEBUG:hepbenchmarksuite.hepbenchmarksuite:"
                          "Running plugins synchronously 'pre' for 1.0 minutes.", log.output)
            self.assertIn("DEBUG:hepbenchmarksuite.hepbenchmarksuite:"
                          "Running plugins synchronously 'post' for 2.0 minutes.", log.output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
