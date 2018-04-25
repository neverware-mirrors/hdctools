# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import cros_ec_hardrec_power


class crosEcHardrecPbinitidlePower(cros_ec_hardrec_power.crosEcHardrecPower):
  """Driver for power_state (currently on Fizz) that allows reset to
  work properly.

  On a cold reset, Fizz will retain the state of the DUT prior to the
  cold reset.  Thus, if the DUT was off before the cold reset, it will
  remain off (power button init idle quirk), which breaks the behavior
  of power_state:reset on Fizz.  Adding an extra power button push if
  we detect that the device is off before the reset call.
  """
  _RESET_DELAY = 1

  def _reset_cycle(self):
    """Force a power cycle using cold reset.

    After the call, the DUT will be powered on in normal (not
    recovery) mode; the call is guaranteed to work regardless of
    the state of the DUT prior to the call.  This call must use
    cold_reset to guarantee that the EC also restarts.

    """
    try:
      self._interface.set('ec_uart_regexp', '["power state 3 = S0"]')
      self._interface.set('ec_uart_cmd', 'powerinfo')
      dut_was_off = False
    except Exception:
      dut_was_off = True
    finally:
      self._interface.set('ec_uart_regexp', 'None')

    if dut_was_off:
      self._power_on(self.REC_OFF)
      time.sleep(self._RESET_DELAY)

    self._cold_reset()

