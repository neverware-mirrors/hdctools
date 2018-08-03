# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for common sequences for image management on switchable usb port."""

import time

import hw_driver


# pylint: disable=invalid-name
# Servod driver discovery logic requires this naming convension
class usbImageManager(hw_driver.HwDriver):
  """Driver to handle common tasks on the switchable usb port."""

  # Timeout to wait before giving up on hoping the image usb dev will enumerate
  _WAIT_TIMEOUT = 10

  # Control aliases to the usb mux (and its power) intended for image management
  _IMAGE_MUX = 'image_usbkey_mux'
  _IMAGE_MUX_PWR = 'image_usbkey_pwr'

  def __init__(self, interface, params):
    """Initialize driver by initializing HwDriver."""
    super(usbImageManager, self).__init__(interface, params)
    # This delay is required to safely switch the usb image mux direction
    self._poweroff_delay = params.get('usb_power_off_delay', None)
    if self._poweroff_delay:
      self._poweroff_delay = float(self._poweroff_delay)

  def _Get_image_usbkey_direction(self):
    """Return direction of image usbkey mux."""
    return self._interface.get(self._IMAGE_MUX)

  def _Set_image_usbkey_direction(self, mux_direction):
    """Connect USB flash stick to either servo or DUT.

    This function switches 'usb_mux_sel1' to provide electrical
    connection between the USB port J3 and either servo or DUT side.

    Switching the usb mux is accompanied by powercycling
    of the USB stick, because it sometimes gets wedged if the mux
    is switched while the stick power is on.

    Args:
      mux_direction: map values of "servo_sees_usbkey" or "dut_sees_usbkey".
    """
    self._interface.set(self._IMAGE_MUX_PWR, 'off')
    time.sleep(self._poweroff_delay)
    self._interface.set(self._IMAGE_MUX, mux_direction)
    time.sleep(self._poweroff_delay)
    self._interface.set(self._IMAGE_MUX_PWR, 'on')
    if self._interface.get(self._IMAGE_MUX) == 'servo_sees_usbkey':
      time.sleep(self._WAIT_TIMEOUT)
