import unittest
import math

from hepbenchmarksuite.plugins.timeseries import Timeseries


class TestTimeseries(unittest.TestCase):

    def test_calculate_statistics(self):
        timeseries = Timeseries('load')
        timeseries.append(20)
        timeseries.append(80)

        stats = timeseries.calculate_statistics()

        self.assertTrue(isinstance(stats, dict))

        self.assertEqual(20, stats['min'])
        self.assertEqual(80, stats['max'])
        self.assertEqual(50.0, stats['mean'])
        self.assertEqual(35.0, stats['q25'])
        self.assertEqual(50.0, stats['median'])
        self.assertEqual(65.0, stats['q75'])
        self.assertEqual(71.0, stats['q85'])
        self.assertEqual(77.0, stats['q95'])

    def test_user_defined_statistics(self):
        timeseries = Timeseries('load', 'mean,min,max,q70,q85')
        timeseries.append(20)
        timeseries.append(80)

        stats = timeseries.calculate_statistics()

        self.assertTrue(isinstance(stats, dict))

        self.assertEqual(20, stats['min'])
        self.assertEqual(80, stats['max'])
        self.assertEqual(50.0, stats['mean'])
        self.assertEqual(62.0, stats['q70'])
        self.assertEqual(71.0, stats['q85'])

    def test_explicit_default_statistics(self):
        timeseries = Timeseries('load', 'default')
        timeseries.append(20)
        timeseries.append(80)

        stats = timeseries.calculate_statistics()

        self.assertTrue(isinstance(stats, dict))

        self.assertEqual(20, stats['min'])
        self.assertEqual(80, stats['max'])
        self.assertEqual(50.0, stats['mean'])
        self.assertEqual(35.0, stats['q25'])
        self.assertEqual(50.0, stats['median'])
        self.assertEqual(65.0, stats['q75'])
        self.assertEqual(71.0, stats['q85'])
        self.assertEqual(77.0, stats['q95'])

    def test_list_statistics(self):
        timeseries = Timeseries('cpu-frequency')
        timeseries.append([20,30])
        timeseries.append([10,40])

        stats = timeseries.calculate_statistics()

        self.assertTrue(isinstance(stats, dict))

        self.assertEqual(10, stats['min'])
        self.assertEqual(40, stats['max'])
        self.assertEqual(25.0, stats['mean'])
        self.assertEqual(17.5, stats['q25'])
        self.assertEqual(25.0, stats['median'])
        self.assertEqual(32.5, stats['q75'])
        self.assertEqual(35.5, stats['q85'])
        self.assertEqual(38.5, stats['q95'])

    def test_create_report(self):
        timeseries = Timeseries('cpu-frequency')
        timeseries.append([20,30])
        timeseries.append([10,40])

        start = list(timeseries.get_values().keys())[0]
        end = list(timeseries.get_values().keys())[-1]

        report = timeseries.create_report()

        self.assertTrue(isinstance(report, dict))

        self.assertEqual(start, report['start_time'])
        self.assertEqual(end, report['end_time'])
        self.assertEqual([[20,30],[10,40]], report['values'])
        self.assertEqual(10, report['statistics']['min'])
        self.assertEqual(40, report['statistics']['max'])
        self.assertEqual(25.0, report['statistics']['mean'])
        self.assertEqual(17.5, report['statistics']['q25'])
        self.assertEqual(25.0, report['statistics']['median'])
        self.assertEqual(32.5, report['statistics']['q75'])
        self.assertEqual(35.5, report['statistics']['q85'])
        self.assertEqual(38.5, report['statistics']['q95'])

    def test_clear__resets_state(self):
        timeseries = Timeseries('load')
        timeseries.append(20)
        timeseries.append(80)

        non_empty_stats = timeseries.calculate_statistics()
        assert (len(non_empty_stats) > 0)

        timeseries.clear()
        empty_stats = timeseries.calculate_statistics()
        self.assertTrue(len(empty_stats) == 0)

    def test_missing_value_create_report(self):
        # Initialize Timeseries and append values
        timeseries = Timeseries('cpu-frequency')
        timeseries.append(20)
        timeseries.append(30)
        timeseries.append(10)
        timeseries.append(math.nan)
        timeseries.append(40)

        # Get start and end timestamps
        start = list(timeseries.get_values().keys())[0]
        end = list(timeseries.get_values().keys())[-1]

        # Generate report
        report = timeseries.create_report()

        # Validate report structure and types
        self.assertTrue(isinstance(report, dict))
        self.assertIn('start_time', report)
        self.assertIn('end_time', report)
        self.assertIn('values', report)
        self.assertIn('statistics', report)

        # Validate timestamps and values
        self.assertEqual(start, report['start_time'])
        self.assertEqual(end, report['end_time'])
        self.assertEqual([20, 30, 10, math.nan, 40], report['values'])

        # Validate statistics
        stats = report['statistics']
        self.assertEqual(10, stats['min'])
        self.assertEqual(40, stats['max'])
        self.assertAlmostEqual(25.0, stats['mean'], places=1)
        self.assertAlmostEqual(17.5, stats['q25'], places=1)
        self.assertAlmostEqual(25.0, stats['median'], places=1)
        self.assertAlmostEqual(32.5, stats['q75'], places=1)
        self.assertAlmostEqual(35.5, stats['q85'], places=1)
        self.assertAlmostEqual(38.5, stats['q95'], places=1)
        self.assertEqual(5, stats['total_count'])
        self.assertEqual(4, stats['valid_count'])

    # Additional edge cases
    def test_all_nan_values(self):
        timeseries = Timeseries('cpu-frequency')
        timeseries.append(math.nan)
        timeseries.append(math.nan)

        report = timeseries.create_report()

        self.assertEqual(report['values'], [math.nan, math.nan])
        
        # Validate the statistics
        stats = report['statistics']
        self.assertEqual(stats['total_count'], 2)
        self.assertEqual(stats['valid_count'], 0)
        self.assertTrue(math.isnan(stats['min']))
        self.assertTrue(math.isnan(stats['max']))
        self.assertTrue(math.isnan(stats['mean']))
        self.assertTrue(math.isnan(stats['median']))

    def test_empty_timeseries(self):
        timeseries = Timeseries('cpu-frequency')
        report = timeseries.create_report()
        self.assertEqual({}, report['statistics'])  # Expect empty statistics
        self.assertEqual([], report['values'])  # No values in the report

