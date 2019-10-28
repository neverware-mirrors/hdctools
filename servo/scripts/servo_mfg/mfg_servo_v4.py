#!/usr/bin/python2
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
import re
import subprocess
import time

import mfg_servo_common as c

SERVO_V4_BIN = 'servo_v4.bin'
STM_DFU_VIDPID = '0483:df11'
STM_VIDPID = '18d1:501b'
ATM_BIN = 'binfiles/Keyboard.hex'
ATM_LUFA_VIDPID = '03eb:2042'
ATM_DFU_VIDPID = '03eb:2ff4'

CYPRESS_DUT_VID = CYPRESS_V4_VID = '04b4'
CYPRESS_DUT_PID = '6502'
CYPRESS_DUT_VIDPID = '%s:%s' % (CYPRESS_DUT_VID, CYPRESS_DUT_PID)

CYPRESS_V4_PID = '6572'

MACADDR = '00:E0:4C:36:00:02'
LOGNAME = '/var/log/mfg_servo_v4'
TESTERLOGNAME = '/var/log/mfg_servo_v4_run'

RE_MACADDR = re.compile('^([0-9A-Fa-f]{2}[:-]){5}([0-9A-F]{2})$')
RE_SERIALNO = re.compile('^(C[0-9]{10}|N[PDQ][0-9]{5})$')


def build_cmd_get_vid_pid_dir(vid, pid):
  """Build a command to get the usb sysfs directory for dev at vid:pid."""
  usbsysfs = '/sys/bus/usb/devices/*/'
  idpath_template = 'grep -l %s $(find %s -maxdepth 1 -name %s)'
  vidpath = idpath_template % (vid, usbsysfs, 'idVendor')
  pidpath = idpath_template % (pid, usbsysfs, 'idProduct')
  orig_base_cmd = ['comm -12']
  for path in [vidpath, pidpath]:
    orig_base_cmd.append('<(dirname $(%s))' % path)
  return ' '.join(orig_base_cmd)


def force_v4_reenumeration():
  """Force a renumeration of v4 using the hub on it."""
  dir_cmd = build_cmd_get_vid_pid_dir(CYPRESS_V4_VID, CYPRESS_V4_PID)
  get_authorized_path_cmd = 'echo $(realpath $(%s))/authorized' % dir_cmd
  authorize_cmd = 'echo 1 > $(%s)' % get_authorized_path_cmd
  deauthorize_cmd = 'echo 0 > $(%s)' % get_authorized_path_cmd
  try:
    subprocess.check_call(['/bin/bash', '-c', deauthorize_cmd])
    time.sleep(1)
    subprocess.check_call(['/bin/bash', '-c', authorize_cmd])
  except subprocess.CalledProcessError as e:
    raise Exception('Failed to reenumerate v4. %s' % str(e))


def do_macaddr(macaddr, check_only=False):
  """Provision macaddr to Realtek r8152 chip.

  This is not needed for a kernel built with the RTK r8152
  firmware provisioning driver.
  https://chromium-review.googlesource.com/#/c/411325/

  Actual mac provisioning uses:
  # sudo rtunicpg-x86_64 00E04C360001 /93c46

  Must have 'rtunicpg-x86_64' in $PATH to work.

  Args:
    macaddr: str, mac address to write onto eeprom
    check_only: bool, whether to exit after checking if they match

  Raises:
    Exception: if there is an issue querying the mac address
    Exception: if reprogramming the eeprom fails
    Exception: if |macaddr| is not the programmed address at the end
  """
  orig_mac_cmd = (r'cat $(realpath $(%s |'
                  r"sed -r 's|/([0-9.\-]+)|/\1.1/\1.1:1.0/net/*/address|'))"
                  % build_cmd_get_vid_pid_dir(CYPRESS_DUT_VID, CYPRESS_DUT_PID))
  try:
    original_macaddr = subprocess.check_output(['/bin/bash', '-c',
                                                orig_mac_cmd]).strip()
  except subprocess.CalledProcessError as e:
    raise Exception('Failed to query original mac address. %s' % str(e))

  if original_macaddr.upper() == macaddr.upper():
    # Mac is already at the right value. Skip.
    return

  if not check_only:
    # Actually attempt to rewrite.

    cmd = 'rtunicpg %s /93c46' % macaddr.replace(':', '').upper()

    if subprocess.call(cmd, shell=True):
      c.log('Failed to set mac %s' % macaddr)
      raise Exception('Enet', 'Failed to set mac %s' % macaddr)

    c.log('Set macaddr to %r' % macaddr)

  # Always verify
  programmed_macaddr = subprocess.check_output(['/bin/bash', '-c',
                                                orig_mac_cmd]).strip()
  if programmed_macaddr.upper() != macaddr.upper():
    raise Exception('Failed to set mac address to %r. Reporting as %r.' %
                    (macaddr, programmed_macaddr))


def rd_atmega_reg(pty):
  """Get atmega reset signal value.

  Read ioexpander output register (2 for port 0) to determine current value
  of atmega_rst.

  Args:
    pty: object, ptyDriver instance talking to Atmega UART

  Returns:
    int, i2c read result from RST register.
  """
  cmdrd = r'i2cxfer r 1 0x40 2'
  regex_atm = r'(0x[0-9a-f][0-9a-f])\s\[\d+\]'
  # pylint: disable=protected-access
  # Need to issue a command.
  results = pty._issue_cmd_get_results(cmdrd, [regex_atm])[0]
  rd = results[1].strip().strip('\n\r')
  return int(rd, 16)


def do_enable_atmega_dfu(pty):
  """Turn on the dfu mode on atmega.

  Args:
    pty: pty, pty instance talking to Atmega UART
  """
  do_toggle_atmega_dfu(pty, on=True)


def do_disable_atmega_dfu(pty):
  """Turn off the dfu mode on atmega.

  Args:
    pty: pty, pty instance talking to Atmega UART
  """
  do_toggle_atmega_dfu(pty, on=False)


def do_toggle_atmega_dfu(pty, on):
  """Toggle atmega dfu GPIO to |on|.

  Args:
    pty: pty, pty instance talking to Atmega UART
    on: bool, whether to turn the GPIO to on or off
  """
  # pylint: disable=protected-access
  # Need to issue a command.
  # Since it's assert low, invert 'on' before casting it to an int.
  pty._issue_cmd('gpioset ATMEL_HWB_L %d' % int(not on))


def do_disable_atmega(pty):
  """Disable the atmega.

  Args:
    pty: pty, pty instance talking to Atmega UART
  """
  do_toggle_atmega(pty, enable=False)


def do_enable_atmega(pty):
  """Enable the atmega.

  Args:
    pty: pty, pty instance talking to Atmega UART
  """
  do_toggle_atmega(pty, enable=True)


def do_toggle_atmega(pty, enable):
  """Toggle the reset pin on the atmega.

  Enable/disable the atmega by deasserting reset on the servo v4's ioexpander
  via ec console 'pty'.

  Args:
    pty: pty, pty instance talking to Atmega UART
    enable: bool, whether to turn it on or off

  Raises:
    Exception: if toggling fails
  """
  rdmsk = 0x2

  rdreg = rd_atmega_reg(pty)
  enable_state = (rdreg & rdmsk) == rdmsk
  if enable_state and enable:
    c.log('Atmega already enabled.')
    return
  if not (enable_state or enable):
    c.log('Atmega already disabled.')
    return

  # Issue i2c write to enable/disable atmega.
  # Simply flip the bit, as we have already checked before whether the bit
  # is in the state we want.
  wr_val = rdreg ^ rdmsk
  # pylint: disable=protected-access
  # Need to issue a command.
  pty._issue_cmd('i2cxfer w 1 0x40 2 0x%02x' % wr_val)

  # Give it time, at least a hint.
  time.sleep(0.2)

  # Check if it stuck
  rdreg = rd_atmega_reg(pty)
  enable_state = (rdreg & rdmsk) == rdmsk
  if enable_state is not enable:
    err = 'Toggling atmega failed: rd: 0x%02x but wr: 0x%02x' % (rdreg, wr_val)
    c.log(err)
    raise Exception('Atmega', err)


def main():
  parser = argparse.ArgumentParser(description='Image a servo v4 device')
  parser.add_argument('-s', '--serialno', type=str,
                      help='serial number to program', default=None)
  parser.add_argument('-m', '--macaddr', type=str, help='macaddr to program',
                      default=None)
  parser.add_argument('--check_only', action='store_true',
                      help='Only check programming. (This overwrites any '
                      "'no_' arg or force_atmega.)")
  parser.add_argument('--no_flash', action='store_false', help='Skip DFU step',
                      dest='flash', default=True)
  parser.add_argument('--no_serial', action='store_false', dest='serial',
                      default=True, help='Skip any serial checking or writing.')
  parser.add_argument('--no_mac', action='store_false', dest='mac',
                      default=True, help='Skip any mac address checking or '
                      'writing.')
  parser.add_argument('--no_atmega', action='store_false', dest='atmega',
                      default=True, help='Skip Atmega fw writing step.')
  parser.add_argument('--force_atmega', action='store_true',
                      default=False, help='Force atmega fw writing, even if '
                      'it already has a fw - overwrite it. (This overwrites '
                      'no_atmega)')

  args = parser.parse_args()
  # Force atmega means we will definitely do atmega.
  args.atmega = args.atmega or args.force_atmega

  serialno = args.serialno
  macaddr = args.macaddr

  c.setup_tester_logfile(TESTERLOGNAME)

  while True:
    # Fetch barcode values
    if args.serial and not serialno:
      while not serialno:
        serialno = raw_input('Scan serial number barcode: ')
        if RE_SERIALNO.match(serialno):
          print 'Scanned sn %s' % serialno
        else:
          serialno = None
    if args.mac and not macaddr:
      while not macaddr:
        macaddr = raw_input('Scan mac addr barcode: ')
        if RE_MACADDR.match(macaddr):
          print 'Scanned mac %s' % macaddr
        else:
          macaddr = None

    c.setup_logfile(LOGNAME, serialno)

    c.log('Scanned sn %s' % serialno)
    c.log('Scanned mac %s' % macaddr)

    action = 'programming'
    if args.check_only:
      args.serial = args.mac = args.atmega = True
      args.force_atmega = args.flash = False
      action = 'checking'

    if args.flash:
      c.log('\n\n************************************************\n')
      c.log('Plug in servo_v4 via OTG adapter')
      c.wait_for_usb(STM_DFU_VIDPID)
      c.log('Found DFU target')
      c.do_dfu(c.full_servo_bin_path(SERVO_V4_BIN))

    c.log('\n\n************************************************\n')
    c.log('Plug in servo_v4 via normal cable')
    c.wait_for_usb(STM_VIDPID)

    c.log('\n\n************************************************\n')
    c.log('Plug in servo_v4 via DUT cable')
    # Wait for cypress USB hub
    c.wait_for_usb(CYPRESS_DUT_VIDPID)
    # Give the device enough time to come up before initializing tiny_servod.
    time.sleep(0.2)

    if args.serial or args.atmega:
      pty = c.setup_tinyservod(STM_VIDPID, 0)

    if args.atmega:
      if args.check_only:
        c.log('%s only - skipping atmega.' % action)
      else:
        # Wait for atmega dfu, if not already programmed or turn into dfu
        # if forcing programming.
        c.log('%s Atmega' % action)
        do_disable_atmega(pty)
        if args.force_atmega:
          # Force atmega by turning it into dfu mode.
          time.sleep(0.1)
          do_enable_atmega_dfu(pty)
        time.sleep(0.1)
        do_enable_atmega(pty)
        # Wait for atmega boot.
        time.sleep(1)
        if not c.check_usb(ATM_LUFA_VIDPID):
          c.wait_for_usb(ATM_DFU_VIDPID)
          c.do_atmega(c.full_bin_path(ATM_BIN))
          c.log('Done programming Atmega')
          if args.force_atmega:
            # Reset the atmega again to non dfu mode.
            do_disable_atmega(pty)
            do_disable_atmega_dfu(pty)
            time.sleep(0.1)
            do_enable_atmega(pty)
        else:
          c.log('Atmega already programmed')
      c.log('')

    if args.serial:
      c.log('%s sn:%s' % (action, serialno))
      c.do_serialno(serialno, pty, check_only=args.check_only)
      # Since some of the checking depends on serial sysfs file, force v4
      # renumeration here.
      force_v4_reenumeration()
      time.sleep(1.5)
      c.log('Done %s serialno' % action)
      c.log('')

    if args.mac:
      c.log('%s mac:%s' % (action, macaddr))
      do_macaddr(macaddr, check_only=args.check_only)
      c.log('Done %s mac' % action)
      c.log('')

      c.log('Finished %s.' % action)
      c.log('\n\n************************************************\n')
      c.log('PASS')
      c.log('ServoV4, %s, %s, PASS' % (serialno, macaddr))
      c.log('\n\n************************************************\n')

    c.finish_logfile()

    # If we have specified by command line or specified to do neither,
    # don't loop again.
    if args.macaddr or args.serialno or not (args.mac or args.serial):
      break
    macaddr = None
    serialno = None

    print '\n\n************************************************\n'
    print 'Make sure no servo_v4 is plugged'
    c.wait_for_usb_remove(STM_VIDPID)


if __name__ == '__main__':
  main()
