# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for TimelinedStatsManager."""

import copy
import math
import shutil
import tempfile
import time
import unittest

import stats_manager
import timelined_stats_manager


class TestTimelinedStatsManager(unittest.TestCase):

  def setUp(self):
    """Set up data and create a temporary directory to save data and stats."""
    unittest.TestCase.setUp(self)
    self.tempdir = tempfile.mkdtemp()
    self.data = timelined_stats_manager.TimelinedStatsManager()

  def tearDown(self):
    """Delete the temporary directory and its content."""
    shutil.rmtree(self.tempdir)
    unittest.TestCase.tearDown(self)

  def assertColumnHeight(self):
    """Helper to assert that all domains have the same number of samples."""
    heights = set([len(samples) for samples in self.data._data.itervalues()])
    self.assertEqual(1, len(heights))

  def test_NaNAddedOnMissingDomain(self):
    """NaN is added when known domain is missing from samples."""
    samples = [('A', 10), ('B', 10)]
    self.data.AddSamples(samples)
    samples = [('B', 20)]
    self.data.AddSamples(samples)
    # NaN was added as the 2nd sample for A
    self.assertTrue(math.isnan(self.data._data['A'][1]))
    # make sure each column is of the same height
    self.assertColumnHeight()

  def test_NaNPrefillOnNewDomain(self):
    """NaN is prefilled for timeline when encountering new domain."""
    samples = [('B', 20)]
    self.data.AddSamples(samples)
    samples = [('A', 10), ('B', 10)]
    self.data.AddSamples(samples)
    self.assertTrue(math.isnan(self.data._data['A'][0]))
    self.assertEqual(10, self.data._data['A'][1])
    self.assertColumnHeight()

  def test_TimelineIsRelativeToTime(self):
    """Timeline key has the same step-size as Time key, just starts at 0."""
    samples = [('A', 10), ('B', 10)]
    # adding using copy to ensure that the same list doesn't get added mulitple
    # times.
    self.data.AddSamples(copy.copy(samples))
    self.data.AddSamples(copy.copy(samples))
    time.sleep(0.005)
    self.data.AddSamples(copy.copy(samples))
    time.sleep(0.01)
    self.data.AddSamples(copy.copy(samples))
    self.data.CalculateStats()
    timepoints = self.data._data[timelined_stats_manager.TIME_KEY]
    timeline = self.data._data[timelined_stats_manager.TLINE_KEY]
    own_tl = [tp - timepoints[0] for tp in timepoints]
    self.assertEqual(own_tl, timeline)

  def test_DuplicateKeys(self):
    """Error raised when adding samples with a duplicate key."""
    samples = [('A', 10), ('B', 10), ('A', 20)]
    with self.assertRaises(stats_manager.StatsManagerError):
      self.data.AddSamples(samples)

  def test_TrimSamples(self):
    """Ensure that trimming works as expected."""
    self.data.AddSamples([('A', 10)])
    tstart = time.time()
    time.sleep(0.01)
    self.data.AddSamples([('A', 23)])
    self.data.AddSamples([('A', 20)])
    tend = time.time()
    time.sleep(0.01)
    self.data.AddSamples([('A', 10)])
    self.data.TrimSamples(tstart=tstart, tend=tend)
    self.data.CalculateStats()
    # Verify that only the samples between the timestamps are left
    self.assertEqual([23, 20], self.data._data['A'])
    for samples in self.data._data.itervalues():
      # Verify that all domains were trimmed to size 2
      self.assertEqual(2, len(samples))

  def test_TrimSamplesNoStartNoEnd(self):
    """Ensure that the trimming encompasses the whole dataset."""
    orig_samples = [10, 23, 20, 10]
    for sample in orig_samples:
      self.data.AddSamples([('A', sample)])
    self.data.CalculateStats()
    self.data.TrimSamples()
    self.assertEqual(orig_samples, self.data._data['A'])
    for samples in self.data._data.itervalues():
      # Verify that all domains were not trimmed
      self.assertEqual(len(orig_samples), len(samples))

  def test_TrimSamplesDomainEmpty(self):
    """Ensure that the domain is removed if it becomes empty post trimming."""
    self.data.AddSamples([('A', 10)])
    time.sleep(0.01)
    tstart = time.time()
    self.data.TrimSamples(tstart=tstart)
    self.data.CalculateStats()
    # Verify that 'A' has been removed
    self.assertNotIn('A', self.data._data)

  def test_TrimSamplesWithPadding(self):
    """Ensure that trimming with padding works as expected."""
    tstart = time.time()
    time.sleep(0.01)
    self.data.AddSamples([('A', 10)])
    time.sleep(0.02)
    self.data.AddSamples([('A', 23)])
    time.sleep(0.01)
    tend = time.time()
    time.sleep(0.01)
    self.data.AddSamples([('A', 20)])
    self.data.TrimSamples(tstart=tstart, tend=tend, padding=0.02)
    self.data.CalculateStats()
    # Verify that only the samples between the timestamps are left
    self.assertEqual([23, 20], self.data._data['A'])
    for samples in self.data._data.itervalues():
      # Verify that all domains were trimmed to size 2
      self.assertEqual(2, len(samples))

if __name__ == '__main__':
  unittest.main()
