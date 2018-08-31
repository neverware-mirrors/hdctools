#!/usr/bin/env python2
# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servod power measurement utility."""

from __future__ import print_function
import argparse
import logging
import os
import shutil
import signal
import sys
import tempfile
import threading

import client
# This module is just a wrapper around measure_power functionality
import measure_power


class ProgressPrinter(threading.Thread):
  """Print a marker every few seconds to indicate progress.

  Public Attributes:
    stop: Event object to signal end to printing.
  """

  # Default progress marker.
  DOT_MARKER = '.'
  # Rate to print progress marker.
  PROGRESS_UPDATE_RATE = 1.0

  def __init__(self, marker=DOT_MARKER, rate=PROGRESS_UPDATE_RATE,
               stop_signal=None):
    """Initialize constants & prepare thread to run."""
    super(ProgressPrinter, self).__init__()
    self._marker = marker
    self._rate = rate
    if not stop_signal:
      stop_signal = threading.Event()
    self.stop = stop_signal

  def run(self):
    """Print |_marker| every |_rate| seconds until |stop| is set."""
    while not self.stop.is_set():
      sys.stdout.write(self._marker)
      sys.stdout.flush()
      self.stop.wait(self._rate)


def _AddMutuallyExclusiveAction(name, parser, default=True, action='save'):
  """Add both '--do-something' and '--no-do-something' pair to parser.

  This adds a mutually exclusive switch for a boolean action into a parser.
  Adds two flags:
  --%{action}-%{name}
  --no-%{action}-%{name}

  Args:
    name: object on which to perform the action
    parser: parser to attach mutually exclusive group to
    default: default value for boolean switch
    action: action to perform on name
  """

  saver = parser.add_mutually_exclusive_group()
  argname = '--%s-%s' % (action, name)
  noargname = '--no-%s-%s' % (action, name)
  dest = '%s_%s' % (action, name.replace('-', '_'))
  arghelp = '%s %s' % (action, name)
  saver.add_argument(argname, default=default, dest=dest,
                     action='store_true', help=arghelp)
  noarghelp = "don't %s %s" % (action, name)
  saver.add_argument(noargname, default=argparse.SUPPRESS, dest=dest,
                     action='store_false', help=noarghelp)


# pylint: disable=dangerous-default-value
def main(cmdline=sys.argv[1:]):
  parser = argparse.ArgumentParser(
      description='Measure power using servod.',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  # servod connection
  parser.add_argument('--host', default=client.DEFAULT_HOST,
                      help='servod host')
  parser.add_argument('-p', '--port', default=client.DEFAULT_PORT, type=int,
                      help='servod port')
  # power measurement logistics
  parser.add_argument('-f', '--fast', default=False, action='store_true',
                      help='if fast no verification cmds are done')
  parser.add_argument('-w', '--wait', default=0, type=float,
                      help='time (sec) to wait before measuring power')
  parser.add_argument('-t', '--time', default=60, type=float,
                      help='time (sec) to measure power for')
  parser.add_argument('--ina-rate', default=measure_power.DEFAULT_INA_RATE,
                      type=float, help='rate (sec) to query the INAs')
  parser.add_argument('--vbat-rate', default=measure_power.DEFAULT_VBAT_RATE,
                      type=float,
                      help='rate (sec) to query the ec vbat command')
  # output and logging logic
  parser.add_argument('-v', '--verbose', default=False, action='store_true',
                      help='print debug log')
  parser.add_argument('--no-output', default=False, action='store_true',
                      help='do not output anything into stdout')
  parser.add_argument('-o', '--outdir', default=None,
                      help='directory to save data into')
  parser.add_argument('-m', '--message', default=None,
                      help='message to append to each summary file stored')
  _AddMutuallyExclusiveAction('raw-data', parser, default=False)
  _AddMutuallyExclusiveAction('summary', parser)
  # NOTE: if logging gets too verbose, turn default off
  _AddMutuallyExclusiveAction('logs', parser)
  parser.add_argument('--save-all', default=False,
                      help='Equivalent to --save-summary --save-logs '
                      '--save-raw-data. Overwrites any of those if specified.')
  args = parser.parse_args(cmdline)
  # Save all logic
  if args.save_all:
    args.save_logs = args.save_raw_data = args.save_summary = True
  pm_logger = logging.getLogger('')
  pm_logger.setLevel(logging.DEBUG)
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.INFO)
  if args.verbose:
    stdout_handler.setLevel(logging.DEBUG)
  if not args.no_output:
    pm_logger.addHandler(stdout_handler)
  if args.save_logs:
    tmplogfile = tempfile.NamedTemporaryFile()
    logfilehandler = logging.StreamHandler(tmplogfile)
    logfilehandler.setLevel(logging.DEBUG)
    pm_logger.addHandler(logfilehandler)
  pm = measure_power.PowerMeasurement(host=args.host, port=args.port,
                                      ina_rate=args.ina_rate,
                                      vbat_rate=args.vbat_rate,
                                      fast=args.fast)
  # pylint: disable=undefined-variable
  # sleep is used as a preemptible way to sleep & allow for SIGTERM/SIGINT
  sleep = threading.Event()
  progress_printer = ProgressPrinter(stop_signal=sleep)
  setup_done = pm.MeasurePower(wait=args.wait)
  # pylint: disable=g-long-lambda
  handler = lambda signal, _, pm=pm, sleep=sleep: (sleep.set(),
                                                   pm.FinishMeasurement())
  # Ensure that SIGTERM and SIGNINT gracefully stop the measurement
  signal.signal(signal.SIGINT, handler)
  signal.signal(signal.SIGTERM, handler)
  # Wait until measurement is is setup
  setup_done.wait()
  if not args.no_output:
    # Start printing progress once power collection has started
    progress_printer.start()
  # Sleep for measurement time and wait time. Will wake on SIGINT & SIGTERM
  sleep.wait(args.time + args.wait)
  # To ensure the ProgressPrinter also stops printing.
  sleep.set()
  # Indicate that measurement should stop, as ProcessMeasurement sets
  # stop_signal internally as well
  pm.ProcessMeasurement()
  pm.DisplaySummary()
  if args.save_summary:
    pm.SaveSummary(args.outdir, args.message)
  if args.save_raw_data:
    pm.SaveRawData(args.outdir)
  if args.save_logs:
    # pylint: disable=protected-access
    outdir = pm._outdir
    if args.outdir and os.path.isdir(args.outdir):
      outdir = args.outdir
    logfile = os.path.join(outdir, 'logs.txt')
    pm_logger.info('Storing logs at:\n%s', logfile)
    shutil.move(tmplogfile.name, logfile)

if __name__ == '__main__':
  main(sys.argv[1:])
