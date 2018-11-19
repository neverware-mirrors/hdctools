# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to expose power measurement tools in servod."""

import collections
import logging

import hw_driver


class PowerToolsError(hw_driver.HwDriverError):
  """Exceptions for power tools module."""


class powerTools(hw_driver.HwDriver):
  """Implement commands that pertain to power measurement."""

  def __init__(self, interface, params):
    """Init powerTools by storing suffix and rail_type info for command.

    Since each command gets their own drv instance, store the suffix (e.g. _mv)
    for the command, and the rail_type (e.g. 'calib') in the class for later
    retrieval.

    Args:
      interface: servo device interface
      params: params for the control
    """
    super(powerTools, self).__init__(interface, params)
    self._logger = logging.getLogger('')
    self._interface = interface
    self._params = params
    self._rail_type = params['rail_type']
    self._suffix = params.get('suffix', '')

  def _ParseRails(self, rail_type):
    """Helper function to parse out INA power measurement rails.

    Args:
      rail_type: one of 'calib' or 'all' to indicate set of desired rails

    Returns:
      list of rail prefixes for the desired rail type

    Raises:
      PowerToolsError: if |rail_type| not 'all' or 'calib'
    """
    if rail_type not in ['calib', 'all']:
      # No valid rail_type was supplied - raise an error.
      raise PowerToolsError('rail type %r unknown.' % rail_type)
    ctrl_dict = collections.defaultdict(set)
    for ctrl in self._interface._syscfg.syscfg_dict['control']:
      for suffix in ['_mw', '_shuntmv']:
        if ctrl.endswith(suffix):
          ctrl_dict[suffix].add(ctrl[:-len(suffix)])
    if rail_type == 'all':
      return list(ctrl_dict['_shuntmv'])
    if rail_type == 'calib':
      # Take the intersection of mw rails and shuntmv rails to remove _mw ec
      # controls like ppvar_vbat_mw, and also INA rails that are marked as
      # non-calib.
      return list(ctrl_dict['_shuntmv'].intersection(ctrl_dict['_mw']))

  def _Get_rails(self):
    """Retrieve rails then make them into desired controls.

    Note: _Get_Rails does not check if the suffix makes for a valid
          servod control. That is on the config writer/caller.

    Returns:
      list of all rails under |rail_type| with _|self._suffix| appended to each
      name, making it a list of servod controls.
    """
    rails = self._ParseRails(self._rail_type)
    if self._suffix:
      rails = ['%s_%s' % (rail, self._suffix) for rail in rails]
    return rails
