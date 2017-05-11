# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for determining which type of servo is being used."""

import hw_driver
import logging

class servoType(hw_driver.HwDriver):
  """Class to access loglevel controls."""

  def __init__(self, interface, params):
    """Initializes the ServoType driver.

    Args:
      interface: A driver interface object.  This is the servod interface.
      params: A dictionary of parameters, but is ignored.
    """
    self._logger = logging.getLogger('Servo Type')
    self._interface = interface
    self._params = params

  def get(self):
    """Gets the current servo type."""
    return self._interface._version
