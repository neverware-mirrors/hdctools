# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for determining which type of servo is being used."""

import logging
import os

import hw_driver
import servo.servo_logging

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

  def _Get_pid(self):
    """Return servod instance pid"""
    return os.getpid()

  def _Get_serial(self):
    """Gets the current servo serial."""
    return self._interface.get_serial_number(self._interface.MAIN_SERIAL)

  def _Get_config_files(self):
    """Gets the configuration files used for this servo server invocation"""
    xml_files = self._interface._syscfg._loaded_xml_files
    # See system_config.py for schema, but entry[0] is the file name
    return [entry[0] for entry in xml_files]

  def _Set_rotate_logs(self, _):
    """Force a servo log rotation."""
    handlers = [h for h in logging.getLogger().handlers if
                isinstance(h, servo.servo_logging.ServodRotatingFileHandler)]
    self._logger.info('Rotating out the log file per user request.')
    if not handlers:
      self._logger.warn('No ServodRotatingFileHandlers on this instance. noop.')
    for h in handlers:
      h.doRollover()
