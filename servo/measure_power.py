# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servod power measurement module."""
from __future__ import print_function

import logging
import os
import threading
import time

import client
import stats_manager
import timelined_stats_manager

SAMPLE_TIME_KEY = 'Sample_msecs'

# Default sample rate to query ec for battery power consumption
DEFAULT_VBAT_RATE = 60
# Default sample rate to query INAs for power consumption
DEFAULT_INA_RATE = 1

# Powerstate name used when no powerstate is known
UNKNOWN_POWERSTATE = 'S?'


class PowerTrackerError(Exception):
  """Error class to invoke on PowerTracker errors."""


class ServodPowerTracker(threading.Thread):
  """Threaded PowerTracker using servod as power number source.

  This PowerTracker uses servod to sample all |_ctrls| at |_rate|.

  Attributes:
    title: human-readable title of the PowerTracker
  """

  def __init__(self, host, port, stop_signal, ctrls, sample_rate, tag='',
               title='unnamed'):
    """Initialize ServodPowerTracker by making servod proxy & storing ctrls.

    Args:
      host: servod host name
      port: servod port number
      stop_signal: Event object to flag when to stop measuring power
      ctrls: list of servod ctrls to collect power numbers
      sample_rate: rate for collecting samples for |ctrls|
      tag: string to prepend to summary & raw rail file names
      title: human-readable title of the PowerTracker
    """
    super(ServodPowerTracker, self).__init__()
    self._sclient = client.ServoClient(host=host, port=port)
    self._stop_signal = stop_signal
    self._ctrls = ctrls
    self._rate = sample_rate
    self.title = title
    self._stats = timelined_stats_manager.TimelinedStatsManager(smid=tag,
                                                                title=title)
    self._logger = logging.getLogger(type(self).__name__)
    self.daemon = True

  def prepare(self, fast=False, powerstate=UNKNOWN_POWERSTATE):
    """Do any setup work right before number collection begins.

    Args:
      fast: flag to indicate if pre-run work should be "fast" (e.g. no UART)
      powerstate: powerstate to allow for conditional preps based on powerstate
    """
    pass

  def verify(self):
    """Verify by trying to query all ctrls once.

    Raises:
      PowerTrackerError: if verification failed
    """
    try:
      self._sclient.set_get_all(self._ctrls)
    except client.ServoClientError:
      msg = 'Failed to test servod commands. Tested: %s' % str(self._ctrls)
      self._logger.error(msg)
      raise PowerTrackerError(msg)

  def run(self):
    """run power collection thread by querying all |_ctrls| at |_rate| rate.

    Query all |_ctrls| and take timestamp once at the start of |_rate| interval.
    """
    while not self._stop_signal.is_set():
      sample_tuples, duration_ms = self._sample_ctrls(self._ctrls)
      self._stats.AddSamples(sample_tuples)
      self._stop_signal.wait(max(self._rate - (duration_ms / 1000), 0))

  def _sample_ctrls(self, ctrls):
    """Helper to query all servod ctrls, and create (name, value) tuples.

    Args:
      ctrls: list of servod ctrls to sample

    Returns:
      tuple (sample_tuples, duration_ms)
             sample_tuples: a list of (ctrl-name, value) tuples
                            value is a power reading on success, NaN on failure
             duration_ms: time it took to collect the sample, in milliseconds
    """
    start = time.time()
    try:
      samples = self._sclient.set_get_all(ctrls)
    except client.ServoClientError:
      self._logger.warn('Attempt to get commands: %s failed. Recording them'
                        ' all as NaN.', ', '.join(ctrls))
      samples = [float('nan')]*len(ctrls)
    duration_ms = (time.time() - start) * 1000
    sample_tuples = zip(ctrls, samples)
    sample_tuples.append((SAMPLE_TIME_KEY, duration_ms))
    return (sample_tuples, duration_ms)

  def process_measurement(self, tstart=None, tend=None):
    """Process the measurement by calculating stats.

    Args:
      tstart: first timestamp to include. Seconds since epoch
      tend: last timestamp to include. Seconds since epoch

    Returns:
      StatsManager object containing info from the run
    """
    self._stats.TrimSamples(tstart, tend)
    self._stats.CalculateStats()
    return self._stats


class HighResServodPowerTracker(ServodPowerTracker):
  """High Resolution implementation of ServodPowerTracker.

  The difference here is that while ServodPowerTracker sleeps if it finishes
  before |_rate| is up, HighResServodPowerTracker tries to collect as many
  samples as it can during |_rate| before recording the mean of those samples
  as one data point.
  """

  # This buffer is used to ensure that the Tracker doesn't attempt one
  # last reading when there is barely any time left, and starts drifting.
  BUFFER = 0.03

  def run(self):
    """run power collection thread.

    Query all |_ctrls| as much as possible during |_rate| interval before
    reporting the mean of those samples as one data point. Timestamp is taken at
    the end of |_rate| interval.
    """
    while not self._stop_signal.is_set():
      start = time.time()
      end = start + self._rate
      loop_end = end - self.BUFFER
      temp_stats = stats_manager.StatsManager()
      while start < loop_end:
        # Setting duration to _ as this PowerTracker does not need duration
        # to calculate for how long to sleep.
        sample_tuples, _ = self._sample_ctrls(self._ctrls)
        for domain, sample in sample_tuples:
          temp_stats.AddSample(domain, sample)
        start = time.time()
      temp_stats.CalculateStats()
      temp_summary = temp_stats.GetSummary()
      samples = [(measurement, summary['mean']) for
                 measurement, summary in temp_summary.iteritems()]
      self._stats.AddSamples(samples)
      # Sleep until the end of the sample rate
      self._stop_signal.wait(max(0, end - time.time()))

  def process_measurement(self, tstart=None, tend=None):
    """Process the measurement by calculating stats.

    Args:
      tstart: first timestamp to include. Seconds since epoch
      tend: last timestamp to include. Seconds since epoch

    Returns:
      StatsManager object containing info from the run
    """
    # Each data point is the mean of all samples taken during |_rate| interval,
    # and the timestamp of the data point is taken at the end of the |_rate|
    # interval. To ensure that we keep all the data points with at least half of
    # their samples within [tstart, tend], add padding = |_rate| / 2.
    # tstart: add the padding to discard data points with less than half samples
    #         within [tstart, tend].
    # tend: add the padding to avoid losing data points that have at least half
    #       of samples within [tstart, tend].
    self._stats.TrimSamples(tstart, tend, self._rate / 2)
    self._stats.CalculateStats()
    return self._stats


class OnboardINAPowerTracker(HighResServodPowerTracker):
  """Off-the-shelf PowerTracker to measure onboard INAs through servod."""

  def __init__(self, host, port, stop_signal, sample_rate=DEFAULT_INA_RATE):
    """Init by finding onboard INA ctrls."""
    super(OnboardINAPowerTracker, self).__init__(host=host, port=port,
                                                 stop_signal=stop_signal,
                                                 ctrls=[],
                                                 sample_rate=sample_rate,
                                                 tag='onboard',
                                                 title='Onboard INA')
    inas = self._sclient.get('raw_calib_rails')
    if not inas:
      raise PowerTrackerError('No onboard INAs found.')
    self._ctrls = ['%s_mw' % ina for ina in inas]
    self._logger.debug('Following power rail commands found: %s',
                       ', '.join(self._ctrls))
    self._pwr_cfg_ctrls = ['%s_cfg_reg' % ina for ina in inas]

  def prepare(self, fast=False, powerstate=UNKNOWN_POWERSTATE):
    """prepare onboard INA measurement by configuring INAs for powerstate."""
    cfg = 'regular_power' if powerstate in [UNKNOWN_POWERSTATE,
                                            'S0'] else 'low_power'
    cfg_ctrls = ['%s:%s' % (cfg_cmd, cfg) for cfg_cmd in self._pwr_cfg_ctrls]
    try:
      self._sclient.set_get_all(cfg_ctrls)
    except client.ServoClientError:
      self._logger.warn('Power rail configuration failed. Config used: %s',
                        ' '.join(cfg_ctrls))


class ECPowerTracker(ServodPowerTracker):
  """Off-the-shelf PowerTracker to measure power-draw as seen by the EC."""

  def __init__(self, host, port, stop_signal, sample_rate=DEFAULT_VBAT_RATE):
    """Init EC power measurement by setting up ec 'vbat' servod control."""
    self._ec_cmd = 'ppvar_vbat_mw'
    self._avg_ec_cmd = 'avg_ppvar_vbat_mw'
    super(ECPowerTracker, self).__init__(host=host, port=port,
                                         stop_signal=stop_signal,
                                         ctrls=[self._ec_cmd],
                                         sample_rate=sample_rate,
                                         tag='ec',
                                         title='EC')

  def verify(self):
    """ECPowerTracker verify that also checks if avg_ppvar is available."""
    # First verify the normal ctrl.
    super(ECPowerTracker, self).verify()
    # Then get ambitious and check if the newer avg_ppvar_vbat_mw is also
    # available.
    self._ctrls = [self._avg_ec_cmd]
    try:
      super(ECPowerTracker, self).verify()
      # This means that avg_ppvar_vbat_mw worked fine.
    except PowerTrackerError:
      # This means that avg_ppvar_vbat_mw is not supported.
      # Revert back to ppvar_vbat_mw for main ctrls.
      self._ctrls = [self._ec_cmd]

  def prepare(self, fast=False, powerstate=UNKNOWN_POWERSTATE):
    """Reduce the time needed to enter deep-sleep after console interaction."""
    # Do not check for failure or anything, as its a nice-to-have and increases
    # accuracy, but does not impact functionality. Dsleep might also not be
    # available on some EC images.
    self._sclient.set('ec_uart_cmd','dsleep 2')

  def run(self):
    """EC vbat 'run' to ensure the first reading does not use averaging."""
    sample_tuples, duration_ms = self._sample_ctrls([self._ec_cmd])
    # Rewrite the name to be whatever actual control is being used: avg &
    # regular. This is required so that the output is not split into two
    # domains that are really the same: regular & avg.
    adjusted_sample_tuples = []
    for name, sample in sample_tuples:
      if name == self._ec_cmd:
        name = self._ctrls[0]
      adjusted_sample_tuples.append((name, sample))
    self._stats.AddSamples(adjusted_sample_tuples)
    self._stop_signal.wait(max(self._rate - (duration_ms / 1000), 0))
    super(ECPowerTracker, self).run()


class PowerMeasurementError(Exception):
  """Error class to invoke on PowerMeasurement errors."""


class PowerMeasurement(object):
  """Class to perform power measurements using servod.

  PowerMeasurement allows the user to perform synchronous and asynchronous
  power measurements using servod.
  The class performs discovery, configuration, and sampling of power commands
  exposed by servod, and allows for configuration of:
  - rates to measure
  - how to store the data

  Attributes:
    _sclient: servod proxy
    _board: name of board attached to servo
    _stats: collection of power measurement stats after run completes
    _outdir: default outdir to save data to
             After the measurement a new directory is generated
    _processing_done: bool flag indicating if measurement data is processed
    _setup_done: Event object to indicate power collection is about to start
    _stop_signal: Event object to indicate that power collection should stop
    _power_trackers: list of PowerTracker objects setup for measurement
    _fast: if True measurements will skip explicit powerstate retrieval
    _logger: PowerMeasurement logger

    Note: PowerMeasurement garbage collection, or any call to Reset(), will
          result in an attempt to clean up directories that were created and
          left empty.
  """

  DEFAULT_OUTDIR_BASE = '/tmp/power_measurements/'

  PREMATURE_RETRIEVAL_MSG = ('Cannot retrieve information before data '
                             'collection has finished.')

  def __init__(self, host, port, ina_rate=DEFAULT_INA_RATE,
               vbat_rate=DEFAULT_VBAT_RATE, fast=False):
    """Init PowerMeasurement class by attempting to create PowerTrackers.

    Args:
      host: host to reach servod instance
      port: port on host to reach servod instance
      ina_rate: sample rate for servod INA controls
      vbat_rate: sample rate for servod ec vbat command
      fast: if true, no servod control verification is done before measuring
            power, nor the powerstate queried from the EC

    Raises:
      PowerMeasurementError: if no PowerTracker setup successful
    """
    self._fast = fast
    self._logger = logging.getLogger(type(self).__name__)
    self._outdir = None
    self._sclient = client.ServoClient(host=host, port=port)
    self._board = 'unknown'
    if not fast:
      try:
        self._board = self._sclient.get('ec_board')
      except client.ServoClientError:
        self._logger.warn('Failed to get ec_board, setting to unknown.')
    self._processing_done = False
    self._setup_done = threading.Event()
    self._stop_signal = threading.Event()
    self._power_trackers = []
    self._stats = {}
    power_trackers = []
    if ina_rate > 0:
      try:
        power_trackers.append(OnboardINAPowerTracker(host, port,
                                                     self._stop_signal,
                                                     ina_rate))
      except PowerTrackerError:
        self._logger.warn('Onboard INA tracker setup failed.')
    if vbat_rate > 0:
      try:
        power_trackers.append(ECPowerTracker(host, port, self._stop_signal,
                                             vbat_rate))
      except PowerTrackerError:
        self._logger.warn('EC Power tracker setup failed.')
    self.Reset()
    for tracker in power_trackers:
      if not self._fast:
        try:
          tracker.verify()
        except PowerTrackerError:
          self._logger.warn('Tracker %s failed verification. Not using it.',
                            tracker.title)
          continue
      self._power_trackers.append(tracker)
    if not self._power_trackers:
      raise PowerMeasurementError('No power measurement source successfully'
                                  ' setup.')

  def Reset(self):
    """Reset PowerMeasurement object to reuse for a new measurement.

    The same PowerMeasurement object can be used for multiple power
    collection runs on the same servod instance by calling Reset() on
    it. This will wipe the previous run's data to allow for a fresh
    reading.

    Use this when running multiple tests back to back to simplify the code
    and avoid recreating the same PowerMeasurement object again.
    """
    self._stats = {}
    self._setup_done.clear()
    self._stop_signal.clear()
    self._processing_done = False

  def MeasureTimedPower(self, sample_time=60, wait=0,
                        powerstate=UNKNOWN_POWERSTATE):
    """Measure power in the main thread.

    Measure power for |sample_time| seconds before processing the results and
    returning to the caller. After this method returns, retrieving measurement
    results is safe.

    Args:
      sample_time: seconds to measure power for
      wait: seconds to wait before collecting power
      powerstate: (optional) pass the powerstate if known
    """
    setup_done = self.MeasurePower(wait=wait, powerstate=powerstate)
    setup_done.wait()
    time.sleep(sample_time+wait)
    self.FinishMeasurement()

  def MeasurePower(self, wait=0, powerstate=UNKNOWN_POWERSTATE):
    """Measure power in the background until caller indicates to stop.

    Spins up a background measurement thread and then returns events to manage
    the power measurement time.
    This should be used when the main thread needs to do work
    (like an autotest) while power measurements are going on.

    Args:
      wait: seconds to wait before collecting power
      powerstate: (optional) pass the powerstate if known

    Returns:
      Event - |setup_done|
      Caller can wait on |setup_done| to know when setup for measurement is done
    """
    self.Reset()
    measure_t = threading.Thread(target=self._MeasurePower, kwargs=
                                 {'wait': wait,
                                  'powerstate': powerstate})
    measure_t.daemon = True
    measure_t.start()
    return self._setup_done

  def _MeasurePower(self, wait, powerstate=UNKNOWN_POWERSTATE):
    """Power measurement thread method coordinating sampling threads.

    Args:
      wait: seconds to wait before collecting power
      powerstate: (optional) pass the powerstate if known
    """
    if not self._fast and powerstate == UNKNOWN_POWERSTATE:
      try:
        ecpowerstate = self._sclient.get('ec_system_powerstate')
        powerstate = ecpowerstate
      except client.ServoClientError:
        self._logger.warn('Failed to get powerstate from EC.')
    for power_tracker in self._power_trackers:
      power_tracker.prepare(self._fast, powerstate)
    ts = time.strftime('%Y%m%d-%H%M%S', time.localtime(time.time()))
    self._outdir = os.path.join(self.DEFAULT_OUTDIR_BASE, self._board,
                                '%s_%s' % (powerstate, ts))
    # Signal that setting the measurement is complete
    self._setup_done.set()
    # Wait on the stop signal for |wait| seconds. Preemptible.
    self._stop_signal.wait(wait)
    if not self._stop_signal.is_set():
      for power_tracker in self._power_trackers:
        power_tracker.start()

  def FinishMeasurement(self):
    """Signal to stop collection to Trackers before joining their threads."""
    self._stop_signal.set()
    for tracker in self._power_trackers:
      if tracker.isAlive():
        tracker.join()

  def ProcessMeasurement(self, tstart=None, tend=None):
    """Trim data to [tstart, tend] before calculating stats.

    Call FinishMeasurement internally to ensure that data collection is fully
    wrapped up.

    Args:
      tstart: first timestamp to include. Seconds since epoch
      tend: last timestamp to include. Seconds since epoch
    """
    # In case the caller did not explicitly call FinishMeasurement yet.
    self.FinishMeasurement()
    try:
      for tracker in self._power_trackers:
        self._stats[tracker.title] = tracker.process_measurement(tstart, tend)
    finally:
      self._processing_done = True

  def SaveRawData(self, outdir=None):
    """Save raw data of the PowerMeasurement run.

    Files can be read into object by using numpy.loadtxt()

    Args:
      outdir: output directory to use instead of autogenerated one

    Returns:
      List of pathnames, where each path has the raw data for a rail on
      this run

    Raises:
      PowerMeasurementError: if called before measurement processing is done
    """
    if not self._processing_done:
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
    outdir = outdir if outdir else self._outdir
    outfiles = []
    for stat in self._stats.itervalues():
      outfiles.extend(stat.SaveRawData(outdir))
    self._logger.info('Storing raw data at:\n%s', '\n'.join(outfiles))
    return outfiles

  def GetRawData(self):
    """Retrieve raw data for current run.

    Retrieve a dictionary of each StatsManager object this run used, where
    each entry is a dictionary of the rail to raw values.

    Returns:
      A dictionary of the form:
        { 'EC'  : { 'time'              : [0.01, 0.02 ... ],
                    'timeline'          : [0.0, 0.01 ...],
                    'Sample_msecs'      : [0.4, 0.2 ...],
                    'ec_ppvar_vbat_mw'  : [52.23, 87.23 ... ]}
          'Onboard INA' : ... }
      Possible keys are: 'EC', 'Onboard INA'

    Raises:
      PowerMeasurementError: if called before measurement processing is done
    """
    if not self._processing_done:
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
    return {name: stat.GetRawData() for name, stat in self._stats.iteritems()}

  def SaveSummary(self, outdir=None, message=None):
    """Save summary of the PowerMeasurement run.

    Args:
      outdir: output directory to use instead of autogenerated one
      message: message to attach after the summary for each summary

    Returns:
      List of pathnames, where summaries for this run are stored

    Raises:
      PowerMeasurementError: if called before measurement processing is done
    """
    if not self._processing_done:
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
    outdir = outdir if outdir else self._outdir
    outfiles = [stat.SaveSummary(outdir) for stat in self._stats.itervalues()]
    if message:
      for fname in outfiles:
        with open(fname, 'a') as f:
          f.write('\n%s\n' % message)
    self._logger.info('Storing summaries at:\n%s', '\n'.join(outfiles))
    return outfiles

  def GetSummary(self):
    """Retrieve summary of the PowerMeasurement run.

    Retrieve a dictionary of each StatsManager object this run used, where
    each entry is a dictionary of the rail to its statistics.

    Returns:
      A dictionary of the form:
        {'EC':          {'ppvar_vbat_mw': {'count':  1,
                                           'max':    0.0,
                                           'mean':   0.0,
                                           'min':    0.0,
                                           'stddev': 0.0},
                         'Sample_msecs':  {...},
                         'time':          {...},
                         'timeline':      {...}},
         'Onboard INA': {...}}
      Possible keys are: 'EC', 'Onboard INA'

    Raises:
      PowerMeasurementError: if called before measurement processing is done
    """
    if not self._processing_done:
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
    return {name: stat.GetSummary() for name, stat in self._stats.iteritems()}

  def GetFormattedSummary(self):
    """Retrieve summary of the PowerMeasurement run.

    See StatsManager._DisplaySummary() for more details

    Returns:
      string with all available summaries concatenated

    Raises:
      PowerMeasurementError: if called before measurement processing is done
    """
    if not self._processing_done:
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
    summaries = [stat.SummaryToString() for stat in self._stats.itervalues()]
    return '\n'.join(summaries)

  def DisplaySummary(self):
    """Print summary retrieved from GetFormattedSummary() call."""
    print('\n%s' % self.GetFormattedSummary())

  # TODO(coconutruben): make it possible to export graphs here
  # graphs should be output in SVG & some interactive HTML format,
  # since that'll make for nice scaling. Also nice to attach to bugs
