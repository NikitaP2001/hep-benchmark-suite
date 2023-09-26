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
        self.assertEqual(50, stats['mean'])

    def test_clear__resets_state(self):
        timeseries = Timeseries('load')
        timeseries.append(20)
        timeseries.append(80)

        non_empty_stats = timeseries.calculate_statistics()
        assert (len(non_empty_stats) > 0)

        timeseries.clear()
        empty_stats = timeseries.calculate_statistics()
        self.assertTrue(len(empty_stats) == 0)
