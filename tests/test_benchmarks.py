#!/usr/bin/env python3
"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""

import unittest
from unittest.mock import patch, mock_open, MagicMock
from hepbenchmarksuite import benchmarks
from hepbenchmarksuite import utils
from hepscore.hepscore import HEPscore
from importlib_metadata import version, PackageNotFoundError
from pkg_resources import parse_version
import sys
import subprocess
import pytest
import yaml


class TestHepscore(unittest.TestCase):
    """Test extra utility methods."""

    def setUp(self):
        self.conf = {'global': {'mode': 'singularity', 'rundir': '/tmp'}, 'hepscore': {'version': 'v1.0rc8', 'config' : 'default' }}

    def test_hepscore_install(self):
        """Test hepscore installation."""
        test_conf = self.conf.copy()

        # Testing this call prep_hepscore works fine with pytest
        # but it fails under tox environment.
        # Hence, the test is based on the logs repporting only
        with self.assertLogs('hepbenchmarksuite.benchmarks', level='INFO') as log:
            ret = benchmarks.prep_hepscore(self.conf)
            self.assertIn('Found existing installation of hep-score in the system', " ".join(log.output))

    @patch.dict(benchmarks.sys.modules, {'hepscore': None})
    def test_hepscore_import(self):
        """Test hepscore missing reports failure."""
        ret = benchmarks.run_hepscore(self.conf)
        self.assertEqual(ret, -1)

    def test_hepscore_missing_conf(self):
        """Test missing hepscore section in config."""

        test_conf = {}

        with self.assertRaises(SystemExit) as context:
            benchmarks.run_hepscore(test_conf)

        self.assertEqual(context.exception.code, 1)


#--------------------------------------------------------------------------------------------------------------
# HEPspec06 and SPEC2017 interface related tests
#-------------------------------------------------------------------------------------------------------------


def alternate_exec(arg, env=None):
    """ Custom function to mock utils.exec_live_output """
    return arg


# It does not inherit from unittest.TestCase to allow using
# pytest.parametrization without issues.
class TestSpec:

    def setup(self):
        """ Load CI configuration """

        with open("tests/ci/benchmarks.yml", 'r') as cfg_file:
            self.config_file = yaml.full_load(cfg_file)
            self.config_file['global']['parent_dir']='.'

    def test_invalid_docker_image(self):
        """ Test if docker image fails if it does not start with docker:// """

        self.setup()
        cont = unittest.TestCase()

        sample_config = self.config_file.copy()
        sample_config['spec2017']['image']='gitlab.com/'
        sample_config['global']['mode']='docker'

        with cont.assertLogs('hepbenchmarksuite.benchmarks', level='INFO') as log:
            assert benchmarks.run_hepspec(sample_config, 'spec2017') == 1
            cont.assertIn('ERROR:hepbenchmarksuite.benchmarks:Invalid docker image specified. Image should start with docker://', " ".join(log.output))

    @pytest.mark.parametrize('bench', ["spec2017", "hs06"])
    @pytest.mark.parametrize('mode', ["docker", "singularity"])
    @patch.object(utils, 'exec_live_output', side_effect=alternate_exec)
    def test_cli_interface(self, mock,  mode, bench):
        """ Test interface to run hepspec06 and spec2017 """

        self.setup()
        sample_config = self.config_file.copy()

        sample_config['global']['mode'] = mode
        sample_config['global']['benchmarks'] = bench

        if bench == "hs06":
            bmkset = '453.povray'
        elif bench == 'spec2017':
            bmkset = '508.namd_r'

        params = [f'-b {bench}',
                   '-w /tmp/hep-spec_wd3',
                   '-n None',
                   '-u https://www.example.com/',
                   '-p /tmp/SPEC',
                   '-i 1',
                   f'-s {bmkset}']

        if mode == 'singularity':
            command_start = 'singularity run'
            params.extend(['-B /tmp/hep-spec_wd3:/tmp/hep-spec_wd3',
                           '-B /tmp/SPEC:/tmp/SPEC',
                           'docker://gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:qa'])
        elif mode == 'docker':
            command_start = 'docker run'
            params.extend(['--rm',
                           '--network=host',
                           '-v /tmp/hep-spec_wd3:/tmp/hep-spec_wd3:Z',
                           '-v /tmp/SPEC:/tmp/SPEC:Z',
                           'gitlab-registry.cern.ch/hep-benchmarks/hep-spec/hepspec-cc7-multiarch:qa'])

        command = str(benchmarks.run_hepspec(sample_config, bench))
        assert command.startswith(command_start)

        for param in params:
            assert param in command


# ----------------------------------------------------------
# This section should be ported to HEP-SCORE unittest
#
#    @patch.object(HEPscore, 'write_output')
#    @patch.object(HEPscore, 'run', return_value=-1)
#    def test_hepscore_loadconf(self, mock_hepscore, mock_writer):
#        test_conf = self.conf.copy()
#        print(test_conf)
#        ret = utils.run_hepscore(test_conf)
#        mock_hepscore.assert_called()
#        mock_writer.assert_called()
#        self.assertIn('hepscore_benchmark', test_conf)
#        self.assertEqual(ret, -1)
#        self.assertEqual('singularity', test_conf['hepscore_benchmark']['settings']['container_exec'])
#
#    @patch.object(utils, 'files', side_effect=Exception('Boom!'))
#    def test_hepscore_loadconf_failure(self, mock_files):
#        test_conf = self.conf.copy()
#        self.assertNotIn('hepscore_benchmark', test_conf)
#        with self.assertLogs('hepbenchmarksuite.utils', level='ERROR') as log:
#            ret = utils.run_hepscore(test_conf)
#            self.assertEqual(ret, -1)
#            self.assertIn('Unable to load default config yaml', *log.output)
#
#    @patch.object(HEPscore, 'write_output')
#    @patch.object(HEPscore, 'run', return_value=-1)
#    def test_hepscore_override_conf(self, mock_hepscore, mock_writer):
#        test_conf = self.conf.copy()
#        test_conf.update({'hepscore_benchmark': {'settings': {}}})
#        with self.assertRaises(SystemExit):
#            utils.run_hepscore(test_conf)
#
#    @patch.object(HEPscore, 'write_output')
#    @patch.object(HEPscore, 'gen_score')
#    @patch.object(HEPscore, 'run', return_value=1)
#    def test_hepscore_genscore(self, mock_hepscore, mock_gen, mock_write):
#        test_conf = self.conf.copy()
#
#        ret = utils.run_hepscore(test_conf)
#        self.assertEqual(ret, 1)
#        mock_gen.assert_called()
#        mock_write.assert_called_once_with('json', '/tmp/HEPSCORE/hepscore_result.json')


if __name__ == '__main__':
    unittest.main(verbosity=2)
