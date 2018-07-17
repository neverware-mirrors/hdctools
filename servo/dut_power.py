#!/usr/bin/env python2
# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servod power measurement utility."""
from __future__ import print_function
import argparse
import logging
import sys

import client
# This module is just a wrapper around measure_power functionality
import measure_power


def main(cmdline=sys.argv[1:]):
  parser = argparse.ArgumentParser(description='Measure power using servod.')
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
  args = parser.parse_args(cmdline)
  pm_logger = logging.getLogger('')
  pm_logger.setLevel(logging.DEBUG)
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.INFO)
  if args.verbose:
    stdout_handler.setLevel(logging.DEBUG)
  if not args.no_output:
    pm_logger.addHandler(stdout_handler)
  pm = measure_power.PowerMeasurement(host=args.host, port=args.port,
                                      ina_rate=args.ina_rate,
                                      vbat_rate=args.vbat_rate,
                                      fast=args.fast)
  pm.MeasureTimedPower(sample_time=args.time, wait=args.wait)
  pm.DisplaySummary()

if __name__ == '__main__':
  main(sys.argv[1:])
