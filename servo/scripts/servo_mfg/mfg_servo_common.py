#!/usr/bin/python2
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to test and flash servo v4 boards.

This script holds functionality shared between
various servo manufacturiong scripts.
"""

import errno
from distutils import sysconfig
import os
import subprocess
import time

import pty_driver
import servo_updater
import stm32uart

logfile = None
testerlogfile = None

def full_servo_bin_path(binfile):
  return os.path.join(servo_updater.FIRMWARE_PATH, binfile)

def full_bin_path(binfile):
  return os.path.join(os.path.dirname(os.path.realpath(__file__)), binfile)

def open_logfile(filename):
  """Open a file and create directory structure if needed."""
  if not os.path.exists(os.path.dirname(filename)):
    try:
      os.makedirs(os.path.dirname(filename))
    except OSError as exc:
      if exc.errno != errno.EEXIST:
        raise
  return open(filename, 'a')


def finish_logfile():
  """Finish a logfile and detetch logging."""
  global logfile
  logfile = None


def setup_logfile(logname, serial):
  """Open a logfile for this servo device."""
  global logfile
  if logfile:
    logfile.flush()
    logfile.close()

  filename = '%s_%s_%s.log' % (logname, serial, time.time())
  logfile = open_logfile(filename)


def setup_tester_logfile(testerlogname):
  """Open a logfile for this test session."""
  global testerlogfile

  filename = '%s_%s.log' % (testerlogname, time.time())
  testerlogfile = open_logfile(filename)


def log(output):
  """Print output to console, and any open logfiles."""
  global logfile
  global testerlogfile
  print output
  if logfile:
    logfile.write(output)
    logfile.write('\n')
    logfile.flush()
  if testerlogfile:
    testerlogfile.write(output)
    testerlogfile.write('\n')
    testerlogfile.flush()


def check_usb(vidpid):
  """Check if vidpid is present on the system's USB."""
  if subprocess.call('lsusb -d %s > /dev/null' % vidpid, shell=True):
    return False
  return True


def check_usb_sn(vidpid):
  """Return the serial number of the first USB device with VID:PID vidpid,
  or None if no device is found.

  This will not work well with two of the same device attached.
  """
  sn = None
  try:
    lsusbstr = subprocess.check_output('lsusb -d %s -v | grep iSerial' % vidpid,
                                       shell=True)
    sn = lsusbstr.split()[2]
  except:
    pass

  return sn


def wait_for_usb_remove(vidpid):
  """Wait for USB device with vidpid to be removed."""
  while check_usb(vidpid):
    time.sleep(1)


def wait_for_usb(vidpid):
  """Wait for usb device with vidpid to be present."""
  while not check_usb(vidpid):
    time.sleep(1)


def do_dfu(bin_name):
  """Flash file 'bin_name" to an stm32 DFU target.

  Must have 'dfu-util' and 'flash_stm32.sh' present
  in the current directory to work.
  """
  mfg_dir = os.path.join(sysconfig.get_python_lib(standard_lib=False),
                         'servo_mfg')
  dfu_sh = os.path.join(mfg_dir, 'flash_stm32.sh')
  if subprocess.call('%s %s' % (dfu_sh, bin_name), shell=True):
    log('Flash, Failed to flash stm32: %s' % bin_name)
    raise Exception('Flash', 'Failed to flash %s' % bin_name)


def do_atmega(bin_name):
  """Flash file 'bin_name" to an atmega DFU target.

  Must have 'dfu-programmer' present in the current directory to work.
  """
  if subprocess.call('dfu-programmer atmega32u4 erase --force', shell=True):
    log('Flash, Failed to erase atmega')
    raise Exception('Flash', 'Failed to erase atmega')
  if subprocess.call('dfu-programmer atmega32u4 flash %s' % bin_name,
                     shell=True):
    log('Flash, Failed to flash atmega: %s' % bin_name)
    raise Exception('Flash', 'Failed to flash atmega: %s' % bin_name)


def do_serialno(serialno, pty, check_only=False):
  """Set serialnumber 'serialno' via ec console 'pty'.

  Commands are:
  # > serialno set 1234
  # Saving serial number
  # Serial number: 1234
  """
  cmd = 'serialno '
  if not check_only:
    cmd += 'set %s' % serialno
  # Anchor the regex at the EOL character to be safe.
  regex = 'Serial number: (.*)[\n\r]'

  results = pty._issue_cmd_get_results(cmd, [regex])[0]
  sn = results[1].strip().strip('\n\r')

  if sn == serialno:
    log('Success !')
  else:
    log('Serial number set to %s but saved as %s.' % (serialno, sn))
    raise Exception('Serial Number',
                    'Serial number set to %s but saved as %s.' % (serialno, sn))
  log('Serial set to %s' % sn)


def setup_tinyservod(vidpid, interface):
  """Set up a pty to the servo v4's ec console in order
  to send commands. Returns a pty_driver object.
  """
  vidstr, pidstr = vidpid.split(':')
  vid = int(vidstr, 16)
  pid = int(pidstr, 16)
  suart = stm32uart.Suart(vendor=vid, product=pid, interface=interface,
                          serialname=None)
  suart.run()
  pty = pty_driver.ptyDriver(suart, [])

  return pty
