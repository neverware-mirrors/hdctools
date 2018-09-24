# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for controlling the watchdog."""

import hw_driver


class servoWatchdogError(hw_driver.HwDriverError):
  """Exception class for servo watchdog."""


class servoWatchdog(hw_driver.HwDriver):
  """Class to control the watchdog."""

  def _update_device_disconnect_ok(self, name, disconnect_ok):
    """Update if it's ok for the device to disconnect.

    If it's not ok for the device to disconnect, the watchdog may kill servod.
    If you know you're going to disconnect a device, you should update let servo
    know.

    Args:
      name: String of the interface name or serial number.
      disconnect_ok: True if it's ok if the device can disconnect.

    Raises:
      servoWatchdogError: if the device isn't found.
    """
    serialnames = self._interface.get_servo_serials()
    # If the name isn't a key, then it might be the serialname
    serial = serialnames.get(name, name)
    if serial not in serialnames.values():
      raise servoWatchdogError('Invalid device %s' % name)

    for device in self._interface.get_devices():
      if serial in device.get_id():
        device.set_disconnect_ok(disconnect_ok)
        return
    raise servoWatchdogError('%s is not being tracked' % serial)

  def _get_device_state(self, device):
    """String of the current device state."""
    # The serial names and devices may be initialized in different orders.
    # The name may not be set. Set it if it isn't set.
    if not device.get_name():
      self._set_device_name(device)
    connected_str = '' if device.is_connected() else 'dis'
    disconnect_ok_str = ' (disconnect ok)' if device.disconnect_is_ok() else ''
    name = device.get_name()
    return '%s: %sconnected%s' % (name, connected_str, disconnect_ok_str)

  def _set_device_name(self, device):
    """Set the device name to one of the serial keys."""
    for name, serial in self._interface.get_servo_serials().items():
      if serial in device.get_id():
        device.set_name(name)
        return
    raise servoWatchdogError('%s not found in serialnames' % device)

  def _Get_watchdog(self):
    """Get the connected state of all devices."""
    # add blank line at start, so formatting looks a bit better
    states = ['']
    for device in self._interface.get_devices():
      states.append(self._get_device_state(device))
    return '\n'.join(states)

  def _Set_watchdog_add(self, val):
    """Signal a device may not be disconnected."""
    self._update_device_disconnect_ok(val, False)

  def _Set_watchdog_remove(self, val):
    """Signal a device may be disconnected."""
    self._update_device_disconnect_ok(val, True)
