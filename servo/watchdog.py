# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Watchdog for servo devices falling off the usb stack."""

import logging
import os
import signal
import threading


class DeviceWatchdog(threading.Thread):
  """Watchdog to ensure servod stops when a servo device gets lost.

  Public Attributes:
    done: event to signal that the watchdog functionality can stop
  """

  # Rate in seconds used to poll when a reinit capable device is attached.
  REINIT_POLL_RATE = 0.1

  def __init__(self, servod, poll_rate=1.0):
    """Setup watchdog thread.

    Args:
      servod: servod server the watchdog is watching over.
      poll_rate: poll rate in seconds
    """
    threading.Thread.__init__(self)
    self.daemon = True
    self._logger = logging.getLogger(type(self).__name__)
    self._turndown_signal = signal.SIGTERM
    self.done = threading.Event()
    self._servod = servod
    self._rate = poll_rate
    self._devices = []

    for device in self._servod.get_devices():
      self._devices.append(device)
      if device.reinit_ok():
        self._rate = self.REINIT_POLL_RATE
        self._logger.info('Reinit capable device found. Polling rate set '
                          'to %.2fs.', self._rate)

    # TODO(coconutruben): Here and below in addition to VID/PID also print out
    # the device type i.e. servo_micro.
    self._logger.info('Watchdog setup for devices: %s', self._devices)

  def deactivate(self):
    """Signal to watchdog to stop polling."""
    self.done.set()

  def disconnect(self, device):
    """Helper to turn down servod if device not found.

    Args:
      device: servo device object
    """
    # Device was not found and we can't reinitialize it. End servod.
    self._logger.error('Device - %s - Turning down servod.', device)
    # Watchdog should run in the same process as servod thread.
    os.kill(os.getpid(), self._turndown_signal)
    self.done.set()

  def run(self):
    """Poll |_devices| every |_rate| seconds. Send SIGTERM if device lost."""
    # Devices that need to be reinitialized
    missing_devices = {}
    # Keep track of device numbers to catch issues where a device reenumerates
    # without the watchdog catching it.
    devnums = {dev.get_id(): dev.usb_devnum() for dev in self._devices}
    while not self.done.is_set():
      self.done.wait(self._rate)
      for device in self._devices:
        dev_id = device.get_id()
        if device.is_connected():
          # Device was found. If it is in the disconnected devices, then it
          # needs to be reinitialized.
          # If the device's devnum has changed, then a reenumeration happened
          # that the watchdog missed. This is fine for reeinit capable devices,
          # but not for the rest.
          devnum = device.usb_devnum()
          if devnum != devnums[dev_id]:
            if not device.reinit_ok():
              # Reenumeration here is bad and not recoverable.
              self._logger.error('Device - %s - changed devnum from %d to %d.',
                                 device, devnums[dev_id], devnum)
              self.disconnect(device)
              break
            # Here, the device is reinit_ok()
            # Refresh the device number.
            devnums[device.get_id()] = devnum
            # Need to remove it from the missing_devices if it was there
            # so we know how many are still disconnected.
            missing_devices.pop(dev_id, None)
            if not missing_devices:
              # Once the last missing device has been found again, reinitialize
              # them all.
              self._servod.reinitialize()
        else:
          # Device was not found.
          self._logger.debug('Device - %s not found when polling.', device)
          if not device.reinit_ok():
            self.disconnect(device)
            break
          missing_devices[dev_id] = 1
          device.disconnect()
