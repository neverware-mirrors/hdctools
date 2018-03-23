#!/usr/bin/python
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to test and flash servo v4 boards.

This script will continuously flash new boards in a loop,
consisting of barcode scan, flash, provision, test.

It will produce logfiles in a logfile/ directory for
each servo and for the full run.
"""

import argparse
import subprocess
import time
import re

import mfg_servo_common as c

BIN_NAME = 'binfiles/servo_v4.bin'
STM_DFU_VIDPID = '0483:df11'
STM_VIDPID = '18d1:501b'
ATM_BIN = 'binfiles/Keyboard.hex'
ATM_LUFA_VIDPID = '03eb:2042'
ATM_DFU_VIDPID = '03eb:2ff4'
CYPRESS_DUT_VIDPID = '04b4:6502'

MACADDR = '00:E0:4C:36:00:02'
LOGNAME = 'logfiles/mfg_servo_v4'
TESTERLOGNAME = 'logfiles/mfg_servo_v4_run'

RE_MACADDR = re.compile('^([0-9A-Fa-f]{2}[:-]){5}([0-9A-F]{2})$')
RE_SERIALNO = re.compile('^(C[0-9]{10}|N[PDQ][0-9]{5})$')


def do_macaddr(macaddr, usemodule=False):
  """Provision macaddr to Realtek r8152 chip.

  Process is as follows for rtk programming kernel module:
  # lsmod | grep mii | grep r8152
  # sudo rmmod r815x cdc_ether r8152
  # sudo insmod r8152.ko

  This is not needed for a kernel built with the RTK r8152
  firmware provisioning driver.
  https://chromium-review.googlesource.com/#/c/411325/

  Actual mac provisioning uses:
  # sudo ./rtunicpg-x86_64 /# 0 /efuse /nodeid 00E04C360001

  Must have 'rtunicpg-x86_64' in the current directory to function.
  """
  if subprocess.call('ifconfig | grep eth0 > /dev/null', shell=True):
    c.log('Waiting for enet')
    time.sleep(3)
  if not subprocess.call('ifconfig | grep -i "%s" > /dev/null' % macaddr,
                         shell=True):
    c.log('Macaddr already set to %s' % macaddr)
    return

  if not subprocess.call('lsmod | grep mii | grep r815x', shell=True):
    if subprocess.call('rmmod r815x cdc_ether', shell=True):
      c.log('Failed to remove r815x cdc_ether')
      raise Exception('Enet', 'Failed remove r815x cdc_ether')
  if usemodule:
    if subprocess.call('lsmod | grep mii | grep r8152', shell=True):
      if subprocess.call('sudo insmod r8152.ko', shell=True):
        c.log('Failed to add r8152 ko')
        raise Exception('Enet', 'Failed to add r8152 ko')
  if subprocess.call(
      './rtunicpg-x86_64 /# 0 /efuse /nodeid %s' % macaddr.replace(':', ''),
      shell=True):
    c.log('Failed to set mac %s' % macaddr)
    raise Exception('Enet', 'Failed to set mac %s' % macaddr)

  c.log('Set macaddr')


def do_enable_atmega(pty):
  """Enable the atmega by deasserting reset on the servo v4's ioexpander
  via ec console 'pty'.
  """
  cmdrd = 'i2cxfer r 1 0x40 2'
  cmdwr = 'i2cxfer w 1 0x40 2 0x82'
  regex = '^(.+)$'
  regex_atm = '(0x8[02] .1[23][80].)'

  results = pty._issue_cmd_get_results(cmdrd, [regex_atm])[0]
  rd = results[1].strip().strip('\n\r')
  if rd == '0x82 [130]':
    c.log('Atmega already enabled')
    return True

  if rd != '0x80 [128]':
    c.log('Check atmega enabled failed: [%s]' % rd)
    raise Exception('Atmega', 'Check atmega enabled failed: [%s]' % rd)

  # Issue i2c write to enable atmega
  pty._issue_cmd(cmdwr)

  # Check if it stuck
  results = pty._issue_cmd_get_results(cmdrd, [regex_atm])[0]
  rd = results[1].strip().strip('\n\r')
  if rd != '0x82 [130]':
    c.log('Enable atmega failed: %s' % rd)
    raise Exception('Atmega', 'Enable atmega failed: [%s]' % rd)

  return True


def main():
  parser = argparse.ArgumentParser(description='Image a servo v4 device')
  parser.add_argument('-s', '--serialno', type=str,
                      help='serial number to program', default=None)
  parser.add_argument('-m', '--macaddr', type=str, help='macaddr to program',
                      default=None)
  parser.add_argument('--no_flash', action='store_true', help='Skip DFU step')

  args = parser.parse_args()

  serialno = args.serialno
  macaddr = args.macaddr

  c.setup_tester_logfile(TESTERLOGNAME)

  while (True):
    # Fetch barcode values
    if not serialno:
      done = False
      while not done:
        serialno = raw_input('Scan serial number barcode: ')
        if RE_SERIALNO.match(serialno):
          print 'Scanned sn %s' % serialno
          done = True
    if not macaddr:
      done = False
      while not done:
        macaddr = raw_input('Scan mac addr barcode: ')
        if RE_MACADDR.match(macaddr):
          print 'Scanned mac %s' % macaddr
          done = True

    c.setup_logfile(LOGNAME, serialno)

    c.log('Scanned sn %s' % serialno)
    c.log('Scanned mac %s' % macaddr)

    if not args.no_flash:
      c.log('\n\n************************************************\n')
      c.log('Plug in servo_v4 via OTG adapter')
      c.wait_for_usb(STM_DFU_VIDPID)
      c.log('Found DFU target')
      c.do_dfu(BIN_NAME)

    c.log('\n\n************************************************\n')
    c.log('Plug in servo_v4 via normal cable')
    c.wait_for_usb(STM_VIDPID)

    c.log('\n\n************************************************\n')
    c.log('Plug in servo_v4 via DUT cable')
    # Wait for cypress USB hub
    c.wait_for_usb(CYPRESS_DUT_VIDPID)

    c.log('Programming sn:%s mac:%s' % (serialno, macaddr))

    c.log('Programming sn:%s' % serialno)
    pty = c.setup_tinyservod(STM_VIDPID, 0)
    c.do_serialno(serialno, pty)
    c.log('Done programming serialno')
    c.log('')

    # Wait for atmega dfu, if not already programmed
    c.log('Programming Atmega')
    do_enable_atmega(pty)
    # Wait for atmega boot.
    time.sleep(1)
    if not c.check_usb(ATM_LUFA_VIDPID):
      c.wait_for_usb(ATM_DFU_VIDPID)
      c.do_atmega(ATM_BIN)
      c.log('Done programming Atmega')
    else:
      c.log('Atmega already programmed')
    c.log('')

    c.log('Programming mac:%s' % macaddr)
    do_macaddr(macaddr)
    c.log('Done programming mac')
    c.log('')

    c.log('Finished programming.')
    c.log('\n\n************************************************\n')
    c.log('PASS')
    c.log('ServoV4, %s, %s, PASS' % (serialno, macaddr))
    c.log('\n\n************************************************\n')

    c.finish_logfile()

    # If we have specified by command line don't loop again.
    if args.macaddr or args.serialno:
      break
    macaddr = None
    serialno = None

    print '\n\n************************************************\n'
    print 'Make sure no servo_v4 is plugged'
    c.wait_for_usb_remove(STM_VIDPID)


if __name__ == '__main__':
  main()
