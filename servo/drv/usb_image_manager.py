# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for common sequences for image management on switchable usb port."""

import os
import time

import hw_driver
import servo.servodutil as util


# pylint: disable=invalid-name
# Servod driver discovery logic requires this naming convension
class usbImageManager(hw_driver.HwDriver):
  """Driver to handle common tasks on the switchable usb port."""

  # Polling rate to poll for image usb dev to appear if setting mux to
  # servo_sees_usbkey
  _POLLING_DELAY = 0.1
  # Timeout to wait before giving up on hoping the image usb dev will enumerate
  _WAIT_TIMEOUT = 10

  # Control aliases to the usb mux (and its power) intended for image management
  _IMAGE_MUX = 'image_usbkey_mux'
  _IMAGE_MUX_PWR = 'image_usbkey_pwr'
  _IMAGE_MUX_TO_SERVO = 'servo_sees_usbkey'

  def __init__(self, interface, params):
    """Initialize driver by initializing HwDriver."""
    super(usbImageManager, self).__init__(interface, params)
    # This delay is required to safely switch the usb image mux direction
    self._poweroff_delay = params.get('usb_power_off_delay', None)
    if self._poweroff_delay:
      self._poweroff_delay = float(self._poweroff_delay)
    # This is required to determine if the usbkey is connected to the host
    self._image_usbkey_hub_port = params.get('hub_port', None)

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
    if self._interface.get(self._IMAGE_MUX) == self._IMAGE_MUX_TO_SERVO:
      end = time.time() + self._WAIT_TIMEOUT
      while not self._interface.get('image_usbkey_dev') and time.time() < end:
        time.sleep(self._POLLING_DELAY)

  def _Get_image_usbkey_dev(self):
    """Probe the USB disk device plugged in the servo from the host side.

    Returns:
      USB disk path if one and only one USB disk path is found, otherwise an
      empty string.
    """

    servod = self._interface
    usb_hierarchy = util.UsbHierarchy()
    # Look for own servod usb device
    # pylint: disable=protected-access
    # Need servod information to find own servod instance.
    self_usb = util.UsbHierarchy.GetUsbDevice(servod._vendor,
                                              servod._product,
                                              servod._serialnames['main'])
    # Get your parent from the hierarchy
    hub_on_servo = usb_hierarchy.GetParentPath(self_usb)
    # Image usb is at hub port |self._image_usbkey_hub_port|
    image_usbkey_sysfs = '%s.%s' % (hub_on_servo, self._image_usbkey_hub_port)
    if not os.path.exists(image_usbkey_sysfs):
      return ''
    # Use /sys/block/ entries to see which block device really is just
    # the self_usb
    for candidate in os.listdir('/sys/block'):
      # /sys/block is a link to a sys hw device file
      devicepath = os.path.realpath(os.path.join('/sys/block', candidate))
      # |image_usbkey_sysfs| is also a link to a sys hw device file
      if devicepath.startswith(os.path.realpath(image_usbkey_sysfs)):
        devpath = '/dev/%s' % candidate
        if os.path.exists(devpath):
          return devpath
    return ''
