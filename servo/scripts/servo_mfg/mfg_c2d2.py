#!/usr/bin/python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to test and flash c2d2 boards.

This script will continuously flash new boards in a loop,
consisting of barcode scan, flash, provision, test.

It will produce logfiles in a logfile/ directory for
each device and for the full run.
"""

import argparse
import re
import time

import mfg_servo_common as c

C2D2_BIN = 'c2d2.bin'
STM_DFU_VIDPID = '0483:df11'
STM_VIDPID = '18d1:5041'
LOGNAME = '/var/log/mfg_c2d2'
TESTERLOGNAME = '/var/log/mfg_c2d2_run'

# Example serial number C2012130001
RE_SERIALNO = re.compile(r'^[C]'                        # supplier
                         r'[0-9]{2}'                    # YY
                         r'(0[1-9]|1[0-2])'             # MM
                         r'(0[1-9]|[12][0-9]|3[0-1])'   # DD
                         r'[0-9]{4}$')                  # Serialno suffix

def main():
  parser = argparse.ArgumentParser(description='Image a c2d2 device')
  parser.add_argument('-s', '--serialno', type=str,
                      help='serial number to program', default=None)
  args = parser.parse_args()

  serialno = args.serialno

  c.setup_tester_logfile(TESTERLOGNAME)

  while True:
    # Fetch barcode values
    if not serialno:
      done = False
      while not done:
        serialno = raw_input('Scan serial number barcode: ')
        if RE_SERIALNO.match(serialno):
          print 'Scanned sn %s' % serialno
          done = True

    c.setup_logfile(LOGNAME, serialno)
    c.log('Scanned sn %s' % serialno)

    c.log('\n\n************************************************\n')
    c.log('Plug in c2d2 via OTG adapter')
    c.wait_for_usb(STM_DFU_VIDPID)
    c.log('Found DFU target')
    c.do_dfu(c.full_servo_bin_path(C2D2_BIN))

    c.log('\n\n************************************************\n')
    c.log('Plug in c2d2 via normal cable')
    c.wait_for_usb(STM_VIDPID)
    # We need to wait after c2d2 power on for initialization to complete,
    # as well as to avoid a race condition with the kernel driver.
    # See b/110045723
    time.sleep(1)

    c.log('Programming sn:%s' % serialno)
    pty = c.setup_tinyservod(STM_VIDPID, 3)
    # Wait for console to settle so that console spew doesn't interfere
    # with our automated command parsing.
    time.sleep(1)
    c.do_serialno(serialno, pty)
    c.log('Done programming serialno')
    c.log('')

    c.log('Finished programming.')
    c.log('\n\n************************************************\n')
    c.log('PASS')
    c.log('C2D2, %s, PASS' % serialno)
    c.log('\n\n************************************************\n')

    c.finish_logfile()
    print 'Finished programming.'

    if args.serialno:
      break

    serialno = None


if __name__ == '__main__':
  main()
