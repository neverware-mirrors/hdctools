# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=na.

Presently this is used for the following purposes:
  - chromebox:
    - lid_open control to always return 'not_applicable'
  - set-only controls:
    - pwr_button_hold
    - uart_multicmd
    - cr50_reboot
"""
import hw_driver


class na(hw_driver.HwDriver):
  """Object to access drv=na controls."""

  def __init__(self, interface, params):
    """Constructor."""
    super(na, self).__init__(interface, params)

  def get(self):
    """Return not_applicate"""
    self._logger.debug("na drv called. returning 'not_applicable'.")
    return 'not_applicable'

  def set(self, value):
    """Do nothing"""
    self._logger.debug('na drv called. setting nothing.')
