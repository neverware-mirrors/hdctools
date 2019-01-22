# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import power_state

class sarienPower(power_state.PowerStateDriver):
  """Driver for power_state for Wilco-class boards."""

  # Time in seconds to allow the BIOS and EC to detect the
  # 'rec_mode' signal after cold reset.
  _RECOVERY_DETECTION_DELAY = 5

  # Time in seconds to wait before taking action after cold reset.
  _COLD_RESET_DELAY = 3

  def _reset_cycle(self):
    """Force a power cycle using cold reset."""
    self._cold_reset()
    time.sleep(self._COLD_RESET_DELAY)
    self._interface.power_short_press()

  def _power_on_rec(self):
    """Power on with recovery mode."""
    self._interface.set('rec_mode', self.REC_ON)
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._reset_cycle()
    time.sleep(self._RECOVERY_DETECTION_DELAY)
    self._interface.set('rec_mode', self.REC_OFF)

  def _power_on_normal(self):
    """Power on with in normal mode, i.e., no recovery."""
    self._interface.power_short_press()

  def _power_on(self, rec_mode):
    """Power on in normal or recovery mode."""
    self._cold_reset()
    time.sleep(self._COLD_RESET_DELAY)
    if rec_mode == self.REC_ON:
      self._power_on_rec()
    else:
      self._power_on_normal()

  def _power_off(self):
    """Force power off, even if already off."""
    self._cold_reset()
    time.sleep(self._COLD_RESET_DELAY)
