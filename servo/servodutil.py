# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Collection of servod utilities."""

import os
import re

import usb


class ServodutilError(Exception):
  """General servoduil error class."""
  pass


class UsbHierarchy(object):
  """A helper class to analyze the sysfs hierarchy of USB devices."""

  USB_SYSFS_PATH = '/sys/bus/usb/devices'
  CHILD_RE = re.compile(r'\d+-\d+(\.\d+){1,}\Z')
  BUS_FILE = 'busnum'
  DEV_FILE = 'devnum'

  def __init__(self):
    # Get the current USB sysfs hierarchy.
    self.RefreshUsbHierarchy()

  @staticmethod
  def GetAllUsbDevices(vid_pid_list):
    """Return all associated USB devices which match the given VID/PID's.

    Args:
      vid_pid_list: List of tuple (vid, pid).

    Returns:
      List of usb.core.Device objects.
    """
    all_devices = []
    for vid, pid in vid_pid_list:
      devs = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
      if devs:
        all_devices.extend(devs)
    return all_devices

  @staticmethod
  def GetUsbDevice(vid, pid, serial):
    """Given vendor id, product id, and serial return usb device object.

    Args:
      vid: vendor id
      pid: product id
      serial: serial name

    Returns:
      usb.core.Device object if found otherwise None

    Raises:
      ServodutilError: if more than one device are found with those attributes.
    """
    devices = UsbHierarchy.GetAllUsbDevices([(vid, pid)])
    devs = []
    for device in devices:
      d_serial = usb.util.get_string(device, 256, device.iSerialNumber)
      if d_serial == serial:
        devs.append(device)
    if len(devs) > 1:
      raise ServodutilError('Found %d devices with |vid:%s|, |pid:%s|, '
                            '|serial:%s|. Should not happen.' % (len(devs),
                                                                 str(vid),
                                                                 str(pid),
                                                                 str(serial)))
    return devs[0] if devs else None

  @staticmethod
  def _ResolveUsbSysfsPath(path):
    if not os.path.isabs(path):
      path = os.path.join(UsbHierarchy.USB_SYSFS_PATH, path)
    return path

  @staticmethod
  def DevNumFromSysfs(sysfs_path):
    path = UsbHierarchy._ResolveUsbSysfsPath(sysfs_path)
    devfile = os.path.join(path, UsbHierarchy.DEV_FILE)
    with open(devfile, 'r') as devf:
      return int(devf.read().strip())

  @staticmethod
  def BusNumFromSysfs(sysfs_path):
    path = UsbHierarchy._ResolveUsbSysfsPath(sysfs_path)
    busfile = os.path.join(path, UsbHierarchy.BUS_FILE)
    with open(busfile, 'r') as busf:
      return int(busf.read().strip())

  def RefreshUsbHierarchy(self):
    """Walk through usb sysfs files and gather parent identifiers.

    The usb sysfs dir contains dirs of the following format:
    - 1-2
    - 1-2:1.0
    - 1-2.4
    - 1-2.4:1.0

    The naming convention works like so:
      <roothub>-<hub port>[.port[.port]]:config.interface

    We are only going to be concerned with the roothub, hub port and port.
    We are going to create a hierarchy where each device will store the usb
    sysfs path of its roothub and hub port.  We will also grab the device's
    bus and device number to help correlate to a usb.core.Device object.

    We will walk through each dir and only match on device dirs
    (e.g. '1-2.4') and ignore config.interface dirs.  When we get a hit, we'll
    grab the bus/dev and infer the roothub and hub port from the dir name
    ('1-2' from '1-2.4') and store the info into a dict.

    The dict key will be a tuple of (bus, dev) and value be the sysfs path.

    Returns:
      Dict of tuple (bus,dev) to sysfs path.
    """
    usb_hierarchy = {}
    for usb_dir in os.listdir(self.USB_SYSFS_PATH):
      if self.CHILD_RE.match(usb_dir):
        usb_dir = os.path.join(self.USB_SYSFS_PATH, usb_dir)
        # Remove last element to get to parent hub's location
        parent = '.'.join(usb_dir.split('.')[:-1])
        try:
          dev = UsbHierarchy.DevNumFromSysfs(usb_dir)
          bus = UsbHierarchy.BusNumFromSysfs(usb_dir)
        except IOError:
          # This means no bus/dev files. Skip
          continue

        usb_hierarchy[(bus, dev)] = (usb_dir, parent)

    self._usb_hierarchy = usb_hierarchy

  def GetParentPath(self, usb_device):
    """Return the USB sysfs path of the supplied usb_device's parent.

    Args:
      usb_device: usb.core.Device object.

    Returns:
      SysFS path string of parent of the supplied usb device.
    """
    return self._usb_hierarchy.get((int(usb_device.bus), int(
        usb_device.address)))[1]

  def ShareSameHub(self, usb_servo, usb_candidate):
    """Check if the given USB device shares the same hub with servo v4.

    Args:
      usb_servo: usb.core.Device object of servo v4.
      usb_candidate: usb.core.Device object of USB device canditate.

    Returns:
      True if they share the same hub; otherwise, False.
    """
    usb_servo_parent = self.GetParentPath(usb_servo)
    usb_candidate_parent = self.GetParentPath(usb_candidate)

    if usb_servo_parent is None or usb_candidate_parent is None:
      return False

    # Check the hierarchy:
    #   internal hub <-- servo v4 mcu
    #         \--------- USB candidate
    if usb_servo_parent == usb_candidate_parent:
      return True

    # Check the hierarchy:
    #   internal hub <-- servo v4 mcu
    #         \--------- external hub
    #                          \--------- USB candidate
    # Check having '.' to make sure it is one of the ports of the internal hub.
    if usb_candidate_parent.startswith(usb_servo_parent + '.'):
      return True

    return False
