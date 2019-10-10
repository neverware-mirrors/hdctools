# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for controlling the active servo v4 device."""

import time

import hw_driver


class activeV4DeviceError(hw_driver.HwDriverError):
  """Exception class for active Servo."""


class activeV4Device(hw_driver.HwDriver):
  """Class to the active servo device.

  Servo v4 is the MAIN device in servo, but it doesn't really control the DUT.
  It's just there for ethernet, managing the image on the usb key, and for
  charging.

  There will be a device connected to servo v4 that controls the DUT. We use
  either servo micro or ccd from the type c servo v4. It is possible for servo
  micro and ccd to be used on the same DUT at the same time. Cr50 won't enable
  ccd AP/EC uart when it sees servo micro is connected, because they use the
  same signals and will interfere with eachother. They can both be used with
  servod at the same time, but only one device will have complete control of the
  DUT at a time.

  This class is used to configure which device has complete control of the DUT.
  """

  # Dictionary of the active devices servo v4 supports. With the device type as
  # the key. The value is True if it's a servo flex device.
  V4_DEVICES = {'ccd_cr50' : False, 'servo_micro' : True}

  def init_v4_device_info(self):
    """Initialize the v4 device information.

    This gets the servo type from the servo information and uses that to
    determine what devices can control the DUT and possibly interfere with
    eachother.

    There is a naming scheme for servo_type when there are multiple devices in
    the same servod instance. The main device is first. Secondary devices that
    control the DUT are separated from the main device with '_with_'. If there
    are multiple devices controlling the DUT, then they are separated by
    '_and_'.

    Here are some valid types.
     - servo_v4
     - servo_v4_with_ccd_cr50
     - servo_v4_with_servo_micro_and_ccd_cr50
    """
    servo_type = self._interface.get('servo_type')
    devices = servo_type.split('_with_')[-1].split('_and_')
    usable_devices = set(devices).intersection(self.V4_DEVICES.keys())

    self._interface.v4_device_info = {}
    self._interface.v4_device_info['default'] = devices[0]
    self._interface.v4_device_info['usable_devices'] = list(usable_devices)

  def get_v4_device_info(self, info_type):
    """Get the requested v4 device information.

    Args:
      info_type: The device information key 'default' or 'usable_devices'

    Returns:
      Returns the requested information.
    """
    if not hasattr(self._interface, 'v4_device_info'):
      self.init_v4_device_info()
    return self._interface.v4_device_info.get(info_type)

  def _Set_device(self, device):
    """Configure cr50 to enable using servo micro or ccd."""
    if device == 'default':
      device = self.get_v4_device_info('default')

    devices = self.get_v4_device_info('usable_devices')
    if device not in devices:
      raise activeV4DeviceError('Invalid device %r. Try %r' % (device, devices))
    use_servo = self.V4_DEVICES[device]

    if device == self._Get_device():
      self._logger.info('Active device is already %r', device)
      return

    # The servo micro uart signals are driven when servo micro is powered. These
    # are the signals that interfere with ccd. Disable/enable them based on
    # whether servo micro is supposed to be active.
    uart_en = 'on' if use_servo else 'off'
    self._interface.set('ec_uart_en', uart_en)
    self._interface.set('cpu_uart_en', uart_en)

    # Cr50 can't detect servo if CCD EC uart is enabled. Enable cr50 servo
    # detection just in case ccd is blocking it.
    if self._interface.get('cr50_servo') == 'undetectable' and use_servo:
      self._interface.set('cr50_force_servo_detect', 'on')

    # Give Cr50 enough time to detect the new state.
    time.sleep(2)

    # Once Cr50 detects servo it should always be able to detect it. We don't
    # need force_servo_detect anymore.
    self._interface.set('cr50_force_servo_detect', 'off')

    if device != self._Get_device():
      raise activeV4DeviceError('Could not set %r as active device' % device)

    self._logger.info('active_v4_device: %s', device)

  def _Get_device(self):
    """Return the active device."""
    try:
      servo_state = self._interface.get('cr50_servo')
    except Exception, e:
      self._logger.info('Could not communicate with cr50. %r', str(e))
      return self.get_v4_device_info('default')
    using_servo = servo_state == 'connected'
    for device, use_servo in self.V4_DEVICES.items():
      if use_servo == using_servo:
        return device
    return self.get_v4_device_info('default')
