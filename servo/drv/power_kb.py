# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for power button servo feature."""

import hw_driver
import keyboard_handlers


class PowerKbError(hw_driver.HwDriverError):
  """Error class for powerKb class."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class powerKb(hw_driver.HwDriver):
  """HwDriver wrapper around servod's power key functions."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object; servod in this case.
      params: dictionary of params;
    """
    super(powerKb, self).__init__(interface, params.copy())
    # pylint: disable=protected-access
    self._handler = keyboard_handlers._BaseHandler(self._interface)

  def set(self, duration):
    """Press power button for |duration| seconds.

    Args:
      duration: seconds to hold the key pressed.
    """
    self._handler.power_key(press_secs=duration)
