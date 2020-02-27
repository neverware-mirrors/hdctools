# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Device tool to manage the (usb) servo device."""

import os
import subprocess
import time

import servo.servo_interfaces
import servo.utils.usb_hierarchy as uh
import tool

# VID to find all servo devices.
SERVO_VID = 0x18d1

# List of PID supported for power-cycle. For now, it's only V4.
PWR_CYCLE_PIDS = [servo.servo_interfaces.SERVO_V4_DEFAULTS[0][1]]


class DeviceError(Exception):
  """Device tool error class."""
  pass


class Device(tool.Tool):
  """Class to implement various subtools to manage a servo devices."""

  # Lookup table for action on uhubctl.
  ACTION_DICT = {'on': 0,
                 'off': 1,
                 'reset': 2}

  # Repetitions to perform on the uhubctl command to get it to trigger.
  REPS = 100

  # Time to sleep after reset to let kernel handle sysfs files
  RESET_DEBOUNCE_S = 2

  # time to sleep for the servo device to reenumerate.
  MAX_REINIT_SLEEP_S = 8

  # Polling intervals to find the |devnum| file for reset device.
  REINIT_POLL_SLEEP_S = 0.1

  @property
  def help(self):
    """Tool help message for parsing."""
    return 'Manage servo device.'

  def _usb_path(self, args):
    """Helper to get the device path.

    Args:
      serial: str, servo serial

    Returns:
      /sys/bus/usb/devices/ path to servo with |serial| or None if not found
    """
    # This list is used to find all servos on the system.
    vid_pid_list = [(SERVO_VID, None)]
    devs = uh.Hierarchy.GetAllUsbDeviceSysfsPaths(vid_pid_list)
    for dev_path in devs:
      dev_serial = uh.Hierarchy.SerialFromSysfs(dev_path)
      if dev_serial == serial:
        return dev_path
    return None

  def usb_path(self, args):
    """Retrieve the usb sysfs path for a serial number."""
    dev_path = self._usb_path(args.serial)
    if dev_path:
      self._logger.info(dev_path)
    else:
      self.error('Device with serial %r not found.', args.serial)

  def _run_uhubctl_command(self, hub, port, action):
    """Build |uhubctl| command performing |action| on |hub|'s |port|.

    Args:
      hub: hub-port path i.e. /sys/bus/usb/devices/ dirname of the hub
      port: str, port number on the hub
      action: one of 'on', 'off', 'reset'
    """
    cmd = self._build_and_assert_uhubctl(hub=hub, port=port)
    if action not in self.ACTION_DICT:
      self.error('Action %s unknown', action)
    action_number = self.ACTION_DICT[action]
    # expand command to perform the uhubctl action.
    cmd = cmd + ['-a', str(action_number), '-r', str(self.REPS)]
    try:
      subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
      self.error('Error performing the uhubctl command. ran: "%s". %s.',
                 ' '.join(cmd), str(e))

  def _build_and_assert_uhubctl(self, hub=None, port=None):
    """Assert uhubctl exists and hub/port are known to it (if provided).

    Args:
      hub: hub-port path i.e. /sys/bus/usb/devices/ dirname of the hub
      port: str, port number on the hub

    Returns:
      cmd: a list of args to call the uhubctl command (at hub/port if provided)
    """
    cmd = ['sudo', 'uhubctl']
    try:
      subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
      self.error('uhubctl not available. Be sure to run as sudo. %s',
                 str(e))
    if hub is not None and port is not None:
      # expand the command to check for hub and port existing.
      # casting port to str to ensure we don't accidently pass an int.
      cmd = cmd + ['-l', hub, '-p', str(port)]
      try:
        subprocess.check_output(cmd)
      except subprocess.CalledProcessError as e:
        self.error('hub %s with port %s unknown to uhubctl. '
                   'Be sure the hub is a supported smart hub. %s', hub, port,
                   str(e))
    return cmd

  def _get_hub_and_port(self, dev_path, pid):
    """Get the external hub and port paths for a given |pid|.

    This is its own function, as different devices might have a different
    internal topology. This method has to guarantee to implement all pids
    in PWR_CYCLE_PIDS.

    Args:
      dev_path: /sys/bus/usb/devices/ path for servo
      pid: servo pid

    Returns:
      (hub, port) tuple, where hub is the external hub that the servo is on
                               port is the port on that hub that the servo is on
    """
    # NOTE: if a servo device or configuration should be supported, this is the
    # spot to implement it. If more devices get implemented here, make sure to
    # document the setup under which the user can expect it to work and for the
    # code to guard against other setups.
    # For example: if a servo micro is attached to a servo v4, the code to reset
    # the micro should not just reset the hub that the v4 is hanging on, as that
    # would reset both.
    if pid == servo.servo_interfaces.SERVO_V4_DEFAULTS[0][1]:
      # For servo v4, the dev_path points to the stm that's hanging on
      # an internal usb hub.
      internal_hub = uh.Hierarchy.GetSysfsParentHubStub(dev_path)
      smart_hub_path = uh.Hierarchy.GetSysfsParentHubStub(internal_hub)
      if smart_hub_path:
        # The internal hub is hanging on the smart hub's port. So the last
        # index is the port number.
        port = internal_hub.rsplit('.', 1)[-1]
        smart_hub = os.path.basename(smart_hub_path)
        return (smart_hub, port)
      self.error('Device does not seem to be hanging on a (smart) hub. %r',
                 dev_path)

    self.error('Unimplemented pid: %04x', pid)

  def power_cycle(self, args):
    """Perform a power-cycle on the device using uhubctl."""
    self._build_and_assert_uhubctl()
    dev_path = self._usb_path(args.serial)
    if not dev_path:
      self.error('Device with serial %r not found.', args.serial)
    pid = uh.Hierarchy.ProductIDFromSysfs(dev_path)
    if pid not in PWR_CYCLE_PIDS:
      self.error('pid: 0x%04x currently not supported for usb power cycling. '
                 'Please use one of: %s', pid, ', '.join('0x%04x' % p for p in
                                                         PWR_CYCLE_PIDS))
    # get devnum, and store it
    devnum = uh.Hierarchy.DevNumFromSysfs(dev_path)
    # extract the hub and check whether it's on uhubctl
    hub, port = self._get_hub_and_port(dev_path, pid)
    self._run_uhubctl_command(hub=hub, port=port, action='reset')
    # Sleep a bit to let the device fully fall off, and the sysfs files be
    # renewed.
    time.sleep(self.RESET_DEBOUNCE_S)
    # For |MAX_REINIT_SLEEP_S| seconds, try to find the new devnum for the
    # device.
    end = time.time() + self.MAX_REINIT_SLEEP_S
    while time.time() < end:
      try:
        # check devnum reset
        if devnum == uh.Hierarchy.DevNumFromSysfs(dev_path):
          self.error('devnum stayed the same even though allegedly the device '
                     'was power-cycled. Do not believe the device was power '
                     'cycled.')
        # If |devnum| changed, then the goal is fulfilled. Move on.
        break
      except uh.HierarchyError:
        # The device might not have reenumerated yet. Sample again.
        time.sleep(self.REINIT_POLL_SLEEP_S)
    else:
      # The while loop finished without breaking out e.g. we never read the
      # |devnum| file successfully.
      self.error('unable to read device |devnum| file after %ds. Giving up.',
                 self.MAX_REINIT_SLEEP_S)
    # At the end, no error was encountered, so indicate belief that reset was
    # successful.
    self._logger.info('Successfully power-cycled device with serial %r. '
                      '(At least reasonably confident).', args.serial)

  def add_args(self, tool_parser):
    """Add the arguments needed for this tool."""
    subcommands = tool_parser.add_subparsers(dest='command')
    tool_parser.add_argument('-s', '--serial', required=True,
                             help='serial of servo device on the system.')
    subcommands.add_parser('usb-path',
                           help='Show /sys/bus/usb/devices path of the device')
    subcommands.add_parser('power-cycle',
                           help='Power cycle device using uhubctl if on smart '
                                'hub')
