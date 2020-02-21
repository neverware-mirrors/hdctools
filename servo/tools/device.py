# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Device tool to manage the (usb) servo device."""

import servo.utils.usb_hierarchy as uh
import tool


# VID to find all servo devices.
SERVO_VID = 0x18d1


class DeviceError(Exception):
  """Device tool error class."""
  pass


class Device(tool.Tool):
  """Class to implement various subtools to manage a servo devices."""

  @property
  def help(self):
    """Tool help message for parsing."""
    return 'Manage servo device.'

  def UsbPath(self, args):
    """Retrieve the usb sysfs path for a serial number."""
    # This list is used to find all servos on the system.
    vid_pid_list = [(SERVO_VID, None)]
    devs = uh.Hierarchy.GetAllUsbDeviceSysfsPaths(vid_pid_list)
    for dev_path in devs:
      serial = uh.Hierarchy.SerialFromSysfs(dev_path)
      if serial == args.serial:
        self._logger.info(dev_path)
        return
    self._logger.info('Device with serial %r not found.', args.serial)

  def add_args(self, tool_parser):
    """Add the arguments needed for this tool."""
    subcommands = tool_parser.add_subparsers(dest='command')
    tool_parser.add_argument('-s', '--serial', required=True,
                             help='serial of servo device on the system.')
    subcommands.add_parser('usb-path',
                           help='Show /sys/bus/usb/devices path of the device')
