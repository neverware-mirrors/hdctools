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
    self.tempdir = tempfile.mkdtemp()
    self.data = timelined_stats_manager.TimelinedStatsManager()

  def tearDown(self):
    """Delete the temporary directory and its content."""
    shutil.rmtree(self.tempdir)

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

if __name__ == '__main__':
  unittest.main()
