# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servod's loglevel."""

import logging

import hw_driver
import servo.ec3po_interface
import servo.servo_logging


class loglevel(hw_driver.HwDriver):
  """Class to access loglevel controls."""

  def __init__(self, interface, params):
    """Initializes the loglevel driver.

    Args:
      interface: A driver interface object, but is ignored.
      params: A dictionary of parameters, but is ignored.
    """
    self._interface = interface
    self._params = params

  def set(self, new_level):
    """Changes the current loglevel of the root logger.

    Args:
      new_level: A string containing the new desired log level.

    Raises:
      HwDriverError if passed in an invalid logging level name.
    """
    new_level = new_level.lower()
    root_logger = logging.getLogger()

    try:
      level, fmt_string = servo.servo_logging.LOGLEVEL_MAP[new_level]
    except KeyError:
      raise hw_driver.HwDriverError('Unknown logging level. '
                                    '(known: critical, error, warning,'
                                    ' info, or debug)')
    out_handlers = [handler for handler in root_logger.handlers if not
                    isinstance(handler,
                               servo.servo_logging.ServodRotatingFileHandler)]
    # Set servod's stdout logging level.
    if len(root_logger.handlers) == 1:
      # In this case, servod is logging with basicConfig i.e. the handler
      # is not the gate-keeper, but rather the root logger itself.
      root_logger.setLevel(level)
      # Set EC-3PO's logging level. This is only relevant when filtering through
      # the root-logger and not through the handlers.
      for interface in self._interface._interface_list:
        if isinstance(interface, servo.ec3po_interface.EC3PO):
          interface.set_loglevel(new_level)
    else:
      for handler in out_handlers:
        handler.setLevel(level)
    # Irrespective of basicConfig or handler based logging, the
    # standard handlers need to be reset for this format.
    for handler in out_handlers:
      handler.setFormatter(logging.Formatter(fmt=fmt_string))


  def get(self):
    """Gets the current loglevel of the root logger."""
    root_logger = logging.getLogger()
    if len(root_logger.handlers) == 1:
      # In this case, servod is logging with basicConfig i.e. the handler
      # is not the gate-keeper, but rather the root logger itself.
      cur_level = root_logger.level
    else:
      for handler in root_logger.handlers:
        # The loglevel is the level of any handler that is not the Servod
        # handler as that one is always on debug.
        if not isinstance(handler,
                          servo.servo_logging.ServodRotatingFileHandler):
          # The file logger is always DEBUG and cannot be changed.
          cur_level = handler.level
          break
      else:
        raise hw_driver.HwDriverError('Root logger has no output handlers '
                                      'besides potentially the '
                                      'ServodRotatingFileHandler')
    return logging.getLevelName(cur_level).lower()
