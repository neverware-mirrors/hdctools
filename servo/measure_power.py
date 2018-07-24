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


class PowerTracker(threading.Thread):
  """Abstract base class for threaded PowerTrackers.

  Attributes:
    title: human-readable title of the PowerTracker
    _stop_signal: Event object to flag when to stop measuring power
    _stats: TimelinedStatsManager to keep track of the power numbers collected
    _logger: PowerTracker logger
  """

  def __init__(self, stop_signal, tag, title):
    """Initialize by storing stop_signal & creating TimelinedStatsManager.

    Args:
      stop_signal: Event object to flag when to stop measuring power
      tag: string to prepend to summary & raw rail file names
      title: human-readable title of the PowerTracker
    """
    super(PowerTracker, self).__init__()
    self.title = title
    self._stop_signal = stop_signal
    self._stats = timelined_stats_manager.TimelinedStatsManager(smid=tag,
                                                                title=title)
    self._logger = logging.getLogger(type(self).__name__)
    self.daemon = True

  def verify(self):
    """Verify that the PowerTracker can do its job."""
    pass

  def prepare(self, fast=False, powerstate=UNKNOWN_POWERSTATE):
    """Do any setup work right before number collection begins.

    Args:
      fast: flag to indicate if pre-run work should be "fast" (e.g. no UART)
      powerstate: powerstate to allow for conditional preps based on powerstate
    """
    pass

  def run(self):
    """Run method to collect power numbers. To be implemented by subclasses."""
    raise NotImplementedError('run needs to be implemented for PowerTracker '
                              'subclasses.')

  def process_measurement(self):
    """Process the measurement by calculating stats.

    Returns:
      StatsManager object containing info from the run
    """
    self._stats.CalculateStats()
    return self._stats


class ServodPowerTracker(PowerTracker):
  """PowerTracker using servod as power number source.

  This PowerTracker uses servod to sample all |ctrls| at |sample_rate|.

  Attributes:
    _sclient: servod proxy
    _ctrls: list of servod controls to query
    _rate: rate at which to query controls
  """

  def __init__(self, host, port, stop_signal, ctrls, sample_rate,
               tag='', title='unnamed'):
    """Initialize ServodPowerTracker by making servod proxy & storing ctrls."""
    self._sclient = client.ServoClient(host=host, port=port)
    self._ctrls = ctrls
    self._rate = sample_rate
    super(ServodPowerTracker, self).__init__(stop_signal=stop_signal,
                                             tag=tag,
                                             title=title)

  def verify(self):
    """Verify by trying to query all ctrls once.

    Raises:
      PowerTrackerError: if verification failed
    """
    try:
      self._sclient.set_get_all(self._ctrls)
    except client.ServoClientError:
      raise PowerTrackerError('Failed to test servod commands. Commands tested:'
                              ' %s' % str(self._ctrls))

  def run(self):
    """run power collection thread by querying all |_ctrls| at |_rate| rate."""
    start = time.time()
    while not self._stop_signal.is_set():
      samples = self._get_power_or_nan()
      duration = time.time() - start
      sample_tuples = zip(self._ctrls, samples)
      sample_tuples.append((SAMPLE_TIME_KEY, duration))
      self._stats.AddSamples(sample_tuples)
      self._stop_signal.wait(max(self._rate - duration, 0))
      start = time.time()

  def _get_power_or_nan(self):
    """Helper to query all servod ctrls.

    Returns:
      list of power numbers on success
      list of NaN on failure
    """
    try:
      samples = self._sclient.set_get_all(self._ctrls)
    except client.ServoClientError:
      self._logger.warn('Attempt to get commands: %s failed. Recording them'
                        ' all as NaN.', ', '.join(self._ctrls))
      samples = [float('nan')]*len(self._ctrls)
    return samples


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

    Query all |_ctrls| as much as possible during |_rate| before reporting the
    mean of those samples as one data point.
    """
    while not self._stop_signal.is_set():
      start = time.time()
      end = start + self._rate
      loop_end = end - self.BUFFER
      temp_stats = stats_manager.StatsManager()
      while start < loop_end:
        samples = self._get_power_or_nan()
        duration = time.time() - start
        sample_tuples = zip(self._ctrls, samples)
        sample_tuples.append((SAMPLE_TIME_KEY, duration))
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
    super(ECPowerTracker, self).__init__(host=host, port=port,
                                         stop_signal=stop_signal,
                                         ctrls=[self._ec_cmd],
                                         sample_rate=sample_rate,
                                         tag='ec',
                                         title='EC')


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
    _setup_done: Event object to indicate power collection is about to start
    _stop_signal: Event object to indicate that power collection should stop
    _processing_done: Event object to signal end of measurement processing
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
    self._setup_done = threading.Event()
    self._stop_signal = threading.Event()
    self._processing_done = threading.Event()
    self._power_trackers = []
    self._stats = {}
    power_trackers = []
    try:
      power_trackers.append(OnboardINAPowerTracker(host, port,
                                                   self._stop_signal, ina_rate))
    except PowerTrackerError:
      self._logger.warn('Onboard INA tracker setup failed.')
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
    self._processing_done.clear()
    # this is clean up unused files that might have been created
    self.Cleanup()

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
    signals = self.MeasurePower(wait=wait, powerstate=powerstate)
    setup_done, stop_signal, processing_done = signals
    setup_done.wait()
    time.sleep(sample_time+wait)
    stop_signal.set()
    processing_done.wait()

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
      Tuple of Events - (|setup_done|, |stop_signal|, |processing_done|)
      Caller can wait on |setup_done| to know when setup for measurement is done
      Caller is to set() |stop_signal| when power collection should end
      Caller is then to wait() on processing_done to know that processing
      of the raw data has concluded, and it is safe to retrieve/save/display
    """
    self.Reset()
    measure_t = threading.Thread(target=self._MeasurePower, kwargs=
                                 {'wait': wait,
                                  'powerstate': powerstate})
    measure_t.daemon = True
    measure_t.start()
    return (self._setup_done, self._stop_signal, self._processing_done)

  def _MeasurePower(self, wait, powerstate=UNKNOWN_POWERSTATE):
    """Power measurement thread method coordinating sampling threads.

    Kick off PowerTrackers. On stop signal, processes them before setting the
    processing done signal.

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
    # Signal that setting the measurement is complete
    self._setup_done.set()
    # Wait on the stop signal for |wait| seconds. Preemptible.
    self._stop_signal.wait(wait)
    for power_tracker in self._power_trackers:
      power_tracker.start()
    self._stop_signal.wait()
    try:
      for power_tracker in self._power_trackers:
        power_tracker.join()
        self._stats[power_tracker.title] = power_tracker.process_measurement()
    finally:
      ts = time.strftime('%Y%m%d-%H%M%S', time.localtime(time.time()))
      self._outdir = os.path.join(self.DEFAULT_OUTDIR_BASE, self._board,
                                  '%s_%s' % (powerstate, ts))
      if not os.path.exists(self._outdir):
        os.makedirs(self._outdir)
      self._processing_done.set()


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
    if not self._processing_done.is_set():
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_WARNING)
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
                    'ec_ppvar_vbat_mw'  : [52.23, 87.23 ... ]}
          'Onboard INA' : ... }
      Possible keys are: 'EC', 'Onboard INA'

    Raises:
      PowerMeasurementError: if called before measurement processing is done
    """
    if not self._processing_done.is_set():
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_WARNING)
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
    if not self._processing_done.is_set():
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_WARNING)
    outdir = outdir if outdir else self._outdir
    outfiles = [stat.SaveSummary(outdir) for stat in self._stats.itervalues()]
    if message:
      for fname in outfiles:
        with open(fname, 'a') as f:
          f.write('\n%s\n' % message)
    self._logger.info('Storing summaries at:\n%s', '\n'.join(outfiles))
    return outfiles

  def GetFormattedSummary(self):
    """Retrieve summary of the PowerMeasurement run.

    See StatsManager._DisplaySummary() for more details

    Returns:
      string with all available summaries concatenated

    Raises:
      PowerMeasurementError: if called before measurement processing is done
    """
    if not self._processing_done.is_set():
      raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_WARNING)
    summaries = [stat.SummaryToString() for stat in self._stats.itervalues()]
    return '\n'.join(summaries)

  def DisplaySummary(self):
    """Print summary retrieved from GetFormattedSummary() call."""
    print('\n%s' % self.GetFormattedSummary())

  # TODO(coconutruben): make it possible to export graphs here
  # graphs should be output in SVG & some interactive HTML format,
  # since that'll make for nice scaling. Also nice to attach to bugs

  def Cleanup(self):
    """Go through _outdir and clean any empty folders."""
    if self._outdir:
      if os.path.exists(self._outdir):
        if not os.listdir(self._outdir):
          os.rmdir(self._outdir)
          self._logger.debug('Removing unused directory: %s', self._outdir)
        brd_dir = os.path.dirname(self._outdir)
        if not os.listdir(brd_dir):
          os.rmdir(brd_dir)
          self._logger.debug('Removing unused directory: %s', brd_dir)
