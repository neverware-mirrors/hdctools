# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for determining which type of servo is being used."""

import hw_driver
import logging


class servoMetadata(hw_driver.HwDriver):
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

  def _Get_type(self):
    """Gets the current servo type."""
    return self._interface._version

  def _Get_serial(self):
    """Gets the current servo serial."""
    if self._interface._serialnames[self._interface.MAIN_SERIAL]:
      return self._interface._serialnames[self._interface.MAIN_SERIAL]
    return 'unknown'

  def _Get_config_files(self):
    """Gets the configuration files used for this servo server invocation"""
    xml_files = self._interface._syscfg._loaded_xml_files
    # See system_config.py for schema, but entry[0] is the file name
    return [entry[0] for entry in xml_files]
