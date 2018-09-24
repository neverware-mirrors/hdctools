# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cr50
import fw_wp_state

import hw_driver

class fwWpCcdError(hw_driver.HwDriverError):
  """Exception class for fwWpCcd."""


class fwWpCcd(fw_wp_state.FwWpStateDriver, cr50.cr50):
  """Driver for fw_wp_state for boards with CCD."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(fwWpCcd, self).__init__(interface, params)

  def _force_on(self):
    """Force the firmware to write-protected."""
    self._issue_cmd('wp on')

  def _force_off(self):
    """Force the firmware to not write-protected."""
    self._issue_cmd('wp off')

  def _reset(self):
    """Reset the firmware write-protection state to the system value."""
    self._issue_cmd('wp follow_batt_pres')

  @cr50.restricted_command
  def _get_state(self):
    """Get the firmware write-protection state."""
    # The output string is defined in ec/board/cr50/wp.c
    result = self._issue_cmd_get_results(
        'wp', ['Flash WP:\s*(forced)?\s*(enabled|disabled)'])[0]
    if result is None:
      raise fwWpCcdError('Cannot retrieve wp result on CCD console.')

    if result[2] == 'enabled':
      if result[1] == 'forced':
        return self._STATE_FORCE_ON
      else:
        return self._STATE_ON
    else:
      if result[1] == 'forced':
        return self._STATE_FORCE_OFF
      else:
        return self._STATE_OFF
