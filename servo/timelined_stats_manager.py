# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Calculates statistics for lists of data and pretty print them."""

from __future__ import print_function
import copy
import time

import stats_manager

TIME_KEY = 'time'
TLINE_KEY = 'timeline'


class TimelinedStatsManager(stats_manager.StatsManager):
  """StatsManager extension that automatically keeps a timeline.

  Timestamp gets recorded when the data is added.

  When calculating stats a timeline is also generated that starts at t=0

  Attributes:
    _tkey: key used for the timestamps column
    _tlkey: key used for the timeline column
  """

  # pylint: disable=W0102
  def __init__(self, title='', smid='', hide_domains=[], order=[],
               time_key=TIME_KEY, timeline_key=TLINE_KEY):
    """Initialize by setting time key and setting it to hide in summaries.

    Note: for title, smid, hide_domains, and order see stats_manager.py for
    details on usage.

    Args:
      title: string used as title banner for formatted summary
      smid: StatsManager id used to prepend to output files to ensure uniqueness
      hide_domains: list of domains to hide on formatted summary
      order: domain order for formatted summary
      time_key: key used for timestamp column
      timeline_key: key used for relative timeline column (starts at 0)
    """
    self._tkey = time_key
    self._tlkey = timeline_key
    super(TimelinedStatsManager, self).__init__(title=title,
                                                smid=smid,
                                                hide_domains=hide_domains,
                                                order=order,
                                                accept_nan=True)
    self._hide_domains.append(self._tkey)
    self._hide_domains.append(self._tlkey)

  def CalculateStats(self):
    """Generate relative timeline before calling StatsManager CalculateStats."""
    timeline = self._data[self._tkey]
    timeline = [entry - timeline[0] for entry in timeline]
    self._data[self._tlkey] = timeline
    super(TimelinedStatsManager, self).CalculateStats()

  def AddSample(self, domain, sample):
    """NotImplemented.

    In order to preserve the balanced timeline adding invidual samples is
    discouraged as it might result in uninteded behavior. If you find yourself
    in need of this function, please implement it/raise a bug.

    """
    raise stats_manager.StatsManagerError('TimelinedStatsManager does not '
                                          'support AddSample. Use AddSamples.')

  def AddSamples(self, samples):
    """Record a list of domains and samples.

    Record each (domain, sample) pair and the timestamp when the
    pairs were recorded.

    To avoid timeline discrepancies, this method ensures that each domain in
    |_data| is of equal size. This is accomplished by adding NaN values
    whenever there is no data-point for a domain at a given timestamp.

    Args:
      samples: a list of (domain, sample) tuples
    """
    samples.append((self._tkey, time.time()))
    domains_so_far = set(self._data.keys())
    domains_incoming = set([entry[0] for entry in samples])
    if len(domains_incoming) != len(samples):
      raise stats_manager.StatsManagerError('Domain appears multiple times.')
    # Add a NaN for each previous time-stamp for new domains
    new_domains = domains_incoming - domains_so_far
    nan_col = [float('NaN')] * len(self._data[self._tkey])
    for domain in new_domains:
      self._data[domain] = copy.copy(nan_col)
    # Add a NaN for each known domain that has no sample in |samples|
    known_domains_missing = domains_so_far - domains_incoming
    known_domains_missing_nans = [(domain, float('NaN')) for domain in
                                  known_domains_missing]
    samples.extend(known_domains_missing_nans)
    for domain, sample in samples:
      super(TimelinedStatsManager, self).AddSample(domain, sample)
