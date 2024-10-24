import unittest

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

    def test_clear__resets_state(self):
        timeseries = Timeseries('load')
        timeseries.append(20)
        timeseries.append(80)

        non_empty_stats = timeseries.calculate_statistics()
        assert (len(non_empty_stats) > 0)

        timeseries.clear()
        empty_stats = timeseries.calculate_statistics()
        self.assertTrue(len(empty_stats) == 0)
