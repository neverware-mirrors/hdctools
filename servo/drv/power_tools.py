# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to expose power measurement tools in servod."""

import hw_driver
import logging
import re


class powerTools(hw_driver.HwDriver):
  """Implement commands that pertain to power measurement.

  Attributes:
    _rails: dictionary to cache rail information
    _rails_init: flag to indicate if cache is initialized
  """

  _rails = {}
  _rails_init = False

  def __init__(self, interface, params):
    """Init powerTools by storing suffix and reg_type info for command.

    Since each command gets their own drv instance, store the suffix (e.g. _mv)
    for the command, and the reg_type (e.g. 'calib') in the class for later
    retrieval.
    """
    super(powerTools, self).__init__(interface, params)
    self._logger = logging.getLogger('')
    self._interface = interface
    self._params = params
    self._reg_type = params['reg_type']
    self._suffix = params.get('suffix', '')

  def _InitRails(self):
    """Helper function to parse out INA power measurement rails."""
    all_ctrls = self._interface.doc_all()
    shuntmv_ctrls = re.findall(r"'control_name': '([\w.]*_shuntmv)'", all_ctrls)
    shuntmv_rails = set(
        [ctrl.replace('_shuntmv', '') for ctrl in shuntmv_ctrls])
    mw_ctrls = re.findall(r"'control_name': '([\w.]*_mw)'", all_ctrls)
    mw_rails = set([ctrl.replace('_mw', '') for ctrl in mw_ctrls])
    # Take the union of mw rails and shuntmv rails to remove _mw ec controls,
    # like ppvar_vbat_mw, and also INA rails that are marked as non-calib.
    mw_rails = mw_rails & shuntmv_rails
    powerTools._rails['all'] = list(shuntmv_rails)
    powerTools._rails['calib'] = list(mw_rails)
    powerTools._rails_init = True

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
    if not powerTools._rails_init:
      self._InitRails()
    rails = powerTools._rails[reg_type]
    if suffix:
      rails = ['%s_%s' % (rail, suffix) for rail in rails]
    return rails

  def _Get_rails(self):
    """Prints a list of rails according to reg_type and suffix param.

    A valid suffix makes the return a string of valid servod commands,
    while an empty suffix simply returns a list of stubs showing what
    rails are configured on the servod instance.
    """
    return self._RetrieveRails(self._reg_type, self._suffix)
