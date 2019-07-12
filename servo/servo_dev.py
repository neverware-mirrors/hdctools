# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servod device used by the server and watchdog."""

import logging
import os
import threading

import servo_interfaces
import servodutil


class ServoDeviceError(Exception):
  """General servo device error class."""
  pass


class ServoDevice(object):
  """Device class to track disconnects and device information."""

  # Reinit capable devices.
  REINIT_CAPABLE = set(servo_interfaces.CCD_DEFAULTS)

  # Available attempts to reconnect a device
  REINIT_ATTEMPTS = 100

  def __init__(self, vid, pid, serialname):
    """Servod device constructor.

    Args:
      vid: usb vendor id of FTDI device
      pid: usb product id of FTDI device
      serialname: string of device serialname/number as defined in FTDI eeprom.

    Raises:
      ServoDeviceError the usb device path isn't found.
    """
    self._logger = logging.getLogger('%s - %s' % (type(self).__name__,
                                     serialname))
    self._vendor = vid
    self._product = pid
    self._serialname = serialname
    self._ifaces_available = threading.Event()
    self._reinit_capable = (vid, pid) in self.REINIT_CAPABLE
    self._reinit_attempts = self.REINIT_ATTEMPTS
    usbmap = servodutil.UsbHierarchy()
    dev = servodutil.UsbHierarchy.GetUsbDevice(vid, pid, serialname)
    sysfs_path = usbmap.GetPath(dev)
    if not sysfs_path:
      raise ServoDeviceError('No sysfs path found for device.')
    self._sysfs_path = sysfs_path
    self._name = ''
    self._disconnect_ok = False
    self.connect()

  def __repr__(self):
    return str(self)

  def __str__(self):
    return '%04x:%04x %s' % (self._vendor, self._product, self._serialname)

  def wait(self, wait_time):
    """Wait for the device to reconnect and the interfaces to become available.

    Args:
        wait_time: time to wait in seconds

    Raises:
      ServoDeviceError: if the interfaces aren't available within timeout period
    """
    if not self._ifaces_available.wait(wait_time):
      raise ServoDeviceError('Timed out waiting for interfaces to become '
                             'available.')

  def connect(self):
    """The device connected."""
    # Mark that the interfaces are available.
    self._ifaces_available.set()
    self._reinit_attempts = self.REINIT_ATTEMPTS

  def disconnect(self):
    """The device disconnected."""
    # Mark that the interfaces are unavailable.
    self._ifaces_available.clear()

    # If it's ok for the device to disconnect, allow it to stay disconnected
    # indefinitely.
    if self._disconnect_ok:
      return

    self._reinit_attempts -= 1
    self._logger.debug('%d reinit attempts remaining.', self._reinit_attempts)

  def reinit_ok(self):
    return self._reinit_capable and (self._reinit_attempts > 0)

  def get_id(self):
    """Return a tuple of the device information."""
    return self._vendor, self._product, self._serialname

  def is_connected(self):
    """Returns True if the device is connected."""
    return os.path.exists(self._sysfs_path)

  def get_name(self):
    """Get the name."""
    return self._name

  def set_name(self, name):
    """Set the name."""
    self._name = name

  def set_disconnect_ok(self, disconnect_ok):
    """Set if it's ok for the device to disconnect.

    Don't decrease the reinit_attempts count if this is True. The device can
    be disconnected forever as long as disconnect is ok.

    Args:
      disconnect_ok: True if it's ok for the device to disconnect.
    """
    self._disconnect_ok = disconnect_ok
    self._reinit_attempts = self.REINIT_ATTEMPTS

  def disconnect_is_ok(self):
    """Returns True if it's ok for the device to disconnect."""
    return self._disconnect_ok
