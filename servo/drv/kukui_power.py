# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cros_ec_softrec_power


class kukuiPower(cros_ec_softrec_power.crosEcSoftrecPower):
  """Driver for power_state for Kukui based devices.

  This handles the Kukui devices, which has a special Type-C port that can only
  run USB 2 protocol in host mode.

  Without this, the device has a chance that USB sticks plugged via a external
  powered hub may fail to work, so resetting USB 3 power on each boot is
  required.
  """

  def __init__(self, interface, params):
    super(kukuiPower, self).__init__(interface, params)
    self._usb3_pwr_en = 'usb3_pwr_en'
    if not interface._syscfg.is_control(self._usb3_pwr_en):
      self._usb3_pwr_en = None

  def _set_usb3_pwr_en(self, state):
    """Sets USB3 power (if available) to a new state."""
    if self._usb3_pwr_en:
      self._logger.info('Setting %s to %s', self._usb3_pwr_en, state)
      self._interface.set(self._usb3_pwr_en, state)

  def _power_on_ap(self):
    """Power on the AP after initializing recovery state."""
    self._set_usb3_pwr_en('off')
    super(kukuiPower, self)._power_on_ap()
    self._set_usb3_pwr_en('on')
