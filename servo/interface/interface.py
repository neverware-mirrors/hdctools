# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Base interface imlementing the common API."""

import logging


class Interface(object):
  """Base servo interface interface."""

  def __init__(self, logger_name=None):
    if logger_name is None:
      logger_name = type(self).__name__
    self._logger = logging.getLogger(logger_name)

  @staticmethod
  def Build(**kwargs):
    """Factory method to implement the interface."""
    raise NotImplementedError('Interfaces have to define a factory method.')

  @staticmethod
  def name():
    raise NotImplementedError('Interfaces have to define a name under which '
                              'they can be found.')

  def reinitialize(self):
    """Base reinitialization logic is a noop. Implement in child if needed."""
    pass

  def close(self):
    """Default closer is a noop if nothing has to be done."""
    pass
