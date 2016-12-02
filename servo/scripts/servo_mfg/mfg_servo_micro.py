#!/usr/bin/python
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to test and flash servo micro boards.

This script will continuously flash new boards in a loop,
consisting of barcode scan, flash, provision, test.

It will produce logfiles in a logfile/ directory for
each servo and for the full run.
"""

import argparse
import re

import mfg_servo_common as c

BIN_NAME="binfiles/servo_micro.bin"
STM_DFU_VIDPID = "0483:df11"
STM_VIDPID = "18d1:501a"
serialno = "Uninitialized"
LOGNAME = "logfiles/mfg_servo_micro"
TESTERLOGNAME="logfiles/mfg_servo_micro_run"

RE_SERIALNO = re.compile('^SM(C[0-9]{10}|N[PDQ][0-9]{5})$')


def main():
  parser = argparse.ArgumentParser(description="Image a servo micro device")
  parser.add_argument('-s', '--serialno', type=str,
      help="serial number to program", default=None)
  args = parser.parse_args()

  serialno = args.serialno

  c.setup_tester_logfile(TESTERLOGNAME)

  while(True):
    # Fetch barcode values
    if not serialno:
      done = False
      while not done:
        serialno = raw_input("Scan serial number barcode: ")
        if RE_SERIALNO.match(serialno):
          print "Scanned sn %s" % serialno
          done = True

    c.setup_logfile(LOGNAME, serialno)
    c.log("Scanned sn %s" % serialno)

    c.log("\n\n************************************************\n")
    c.log("Plug in servo_micro via OTG adapter")
    c.wait_for_usb(STM_DFU_VIDPID)
    c.log("Found DFU target")
    c.do_dfu(BIN_NAME)

    c.log("\n\n************************************************\n")
    c.log("Plug in servo_micro via normal cable")
    c.wait_for_usb(STM_VIDPID)

    c.log("Programming sn:%s" % serialno)
    pty = c.setup_tinyservod(STM_VIDPID, 3)
    c.do_serialno(serialno, pty)
    c.log("Done programming serialno")
    c.log("")

    c.log("Finished programming.")
    c.log("\n\n************************************************\n")
    c.log("PASS")
    c.log("Servo_Micro, %s, PASS" % serialno)
    c.log("\n\n************************************************\n")

    c.finish_logfile()
    print "Finished programming."

    if args.serialno:
      break

    serialno = None


if __name__ == "__main__":
  main()
