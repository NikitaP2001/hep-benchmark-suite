import unittest
from parameterized import parameterized
from unittest.mock import patch, MagicMock
import sys
import os
from hepbenchmarksuite import bmkrun
from hepbenchmarksuite.exceptions import PreFlightError
from hepbenchmarksuite.hepbenchmarksuite import HepBenchmarkSuite
import hepbenchmarksuite 

class TestBenchmarkRunnerExitStatus(unittest.TestCase):
    @parameterized.expand([
        # Mock args and expected error codes
        # Fail if no config file specified
        (  
            [], 
            bmkrun.ExitStatus.NO_CONFIG_FILE
        ),
        # Fail if file not found
        (
            ['-c', 'nonexistent_config.yaml'],
            bmkrun.ExitStatus.FILE_NOT_FOUND
        ),
        # Fail if missing benchmark
        (
            [ '-c', os.path.split(__file__)[0]+'/ci/wrong_conf.yml'],
            bmkrun.ExitStatus.MISSING_BENCHMARK
        ),
        # Fail if invalid benchmark specified
        (
            ['-b', 'invalid_benchmark', '-c', os.path.split(__file__)[0]+'/ci/benchmarks.yml'],
            bmkrun.ExitStatus.INVALID_BENCHMARK
        ),
        # Fail if invalid CPU number provided
        (
            ['-b', 'db12', '-c', os.path.split(__file__)[0]+'/ci/wrong_conf.yml'],
            bmkrun.ExitStatus.INVALID_CPU_NUMBER
        ),
        # add other tests if needed
    ])
    def test_exit_statuses(self, cli_args, expected_exit_code):
        with self.assertRaises(SystemExit) as cm:
            sys.argv = ['bmkrun.py']
            sys.argv.extend(cli_args)
            print(cli_args)

            bmkrun.main()
            self.assertEqual(cm.exception.code, expected_exit_code)

    # def test_exit_suite_fails(self):
    #     # This test case may require mocking and patching to simulate the scenario where the suite fails.
    #     # For example, you can mock a failing scenario within the suite and then test the exit code.
    #     # Here's a general structure without actual mocking for the failing suite.
    #     with patch('hepbenchmarksuite.hepbenchmarksuite.HepBenchmarkSuite.start', side_effect=PreFlightError):
    #         with self.assertRaises(SystemExit) as cm:
    #             sys.argv = ['bmkrun.py', '-c', 'default']
    #             main()


    #     # with patch.object(hepscore.HEPscore, 'run') as mock_run, \
    #     #        patch.object(hepscore.HEPscore, 'gen_score') as mock_gen_score, \
    #     #         patch.object(hepscore.HEPscore, 'write_output') as mock_write_output:
        
    #     #     # Prepare the mock HEPscore object
    #     #     mock_run.return_value=0
    #     #     mock_gen_score.return_value=0
    #     #     mock_write_output.return_value=0
    #     self.assertEqual(cm.exception.code, bmkrun.ExitStatus.SUITE_FAILS)

    @patch('hepbenchmarksuite.plugins.send_queue.send_message')
    def test_main_success(self, mock_send_message):
  
        
        # Patch the start() method directly in the HepBenchmarkSuite class
        with patch.object(HepBenchmarkSuite, 'start') as mock_start , \
            patch.object(hepbenchmarksuite.utils,'print_results_from_file'
                         ) as mock_print_results_from_file ,\
                patch.object(hepbenchmarksuite.utils,'export') as mock_export:
            # Set the return value of start() to simulate a successful start
            mock_start.return_value = None
            mock_start.side_effect = None

            # Execute main
            sys_args = ['bmkrun.py', '-c', 'default', '-b', 'hepscore']
            with patch.object(sys, 'argv', sys_args):
                bmkrun.main()

                # Assertions
                mock_start.assert_called_once()  # Verify if start() method was called
                mock_export.assert_not_called()
                mock_send_message.assert_not_called()
                mock_print_results_from_file.assert_called_once()



if __name__ == '__main__':
    unittest.main()
