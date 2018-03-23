# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to expose power measurement tools in servod."""

import hw_driver
import logging
import re


class PowerTools(hw_driver.HwDriver):
  """Implement commands that pertain to power measurement.

  Attributes:
    _rails: dictionary to cache rail information

  """

  _rails = {}

  def __init__(self, interface, params):
    """Init powerTools by setting init to False, and clearing cache."""
    super(powerTools, self).__init__(interface, params)
    self._logger = logging.getLogger('')
    self._interface = interface
    self._params = params
    self._rails = {}
    self._rails_init = False

  def _InitRails(self):
    """Helper function to parse out INA power measurement rails."""
    all_ctrls = self._interface.doc_all()
    shuntmv_ctrls = re.findall(r"'control_name': '(\w*_shuntmv)'", all_ctrls)
    shuntmv_rails = set(
        [ctrl.replace('_shuntmv', '') for ctrl in shuntmv_ctrls])
    mw_ctrls = re.findall(r"'control_name': '(\w*_mw)'", all_ctrls)
    mw_rails = set([ctrl.replace('_mw', '') for ctrl in mw_ctrls])
    # Take the union of mw rails and shuntmv rails to remove _mw ec controls,
    # like ppvar_vbat_mw, and also INA rails that are marked as non-calib.
    mw_rails = mw_rails & shuntmv_rails
    self._rails['all'] = list(shuntmv_rails)
    self._rails['calib'] = list(mw_rails)
    self._rails_init = True

  def _RetrieveRails(self, reg_type, suffix=''):
    """Retrieve rails by checking cache and on miss populating it.

    Note: _RetrieveRails does not check if the suffix makes for a valid
          servod control. That is on the caller.

    Args:
      reg_type: 'calib' to get rails marked as calib or 'all' for all rails
      suffix: suffix to append to each rail to make them into servo controls

    Returns:
      list of all rails under |reg_type| with _|suffix| appended to each
      name, making it a list of servod controls.
    """
    if not self._rails_init:
      self._InitRails()
    rails = self._rails[rail_type]
    if suffix:
      rails = ['%s_%s' % (rail, suffix) for rail in rails]
    return rails

  def _Get_current_rails(self):
    """Prints a list of cmds to measure current on available rails."""
    current_rails = self._RetrieveRails('calib', 'ma')
    return ', '.join(current_rails)

  def _Get_power_rails(self):
    """Prints a list of cmds to measure power on available rails."""
    mw_rails = self._RetrieveRails('calib', 'mw')
    return ', '.join(mw_rails)

  def _Get_shunt_voltage_rails(self):
    """Prints a list of cmds to measure shunt voltage on available rails."""
    shuntmv_rails = self._RetrieveRails('all', 'shuntmv')
    return ', '.join(shuntmv_rails)

  def _Get_bus_voltage_rails(self):
    """Prints a list of cmds to measure bus voltage on available rails."""
    mv_rails = self._RetrieveRails('all', 'mv')
    return ', '.join(mv_rails)

  def _Get_raw_rails(self):
    """Prints a list of cmd prefixes for all INA rails."""
    rails = self._RetrieveRails('all')
    return ', '.join(rails)

  def _Get_raw_calib_rails(self):
    """Prints a list of cmd prefixes for all INA rails marked calib."""
    rails = self._RetrieveRails('calib')
    return ', '.join(rails)
