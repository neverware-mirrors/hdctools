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
    self._on = 'on'
    self._off = 'off'
    if not interface._syscfg.is_control(self._usb3_pwr_en):
      self._usb3_pwr_en = None

  def _reset_usb(self):
    """Resets the USB 3 power (if available and turned on) by turning it off.

    Returns:
      True if reset (i.e., need to restore later), otherwise False.
    """
    if not self._usb3_pwr_en:
      return False

    # Some FAFT tests (e.g, platform_ServoPowerStateController*) will set
    # usb3_pwr_en to off to test booting system into recovery mode (without
    # booting from USB) so we want to reset only when usb3_pwr_en is turned on.
    state = self._interface.get(self._usb3_pwr_en)
    self._logger.debug('%s state: %s', self._usb3_pwr_en, state);
    if state != self._on:
      return False

    self._logger.info('Reset %s to %s', self._usb3_pwr_en, self._off)
    self._interface.set(self._usb3_pwr_en, self._off)
    return True

  def _restore_usb(self):
    """Returns (turns on) USB3 power."""
    self._logger.info('Set %s to %s', self._usb3_pwr_en, self._on)
    self._interface.set(self._usb3_pwr_en, self._on)

  def _power_on_ap(self):
    """Power on the AP after initializing recovery state."""
    need_to_restore = self._reset_usb()

    # b/131856041: Kukui tablets boot only after power button pressed > 1.0s.
    self._interface.set('power_key', 'press')

    if need_to_restore:
      self._restore_usb()
