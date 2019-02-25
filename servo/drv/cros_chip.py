# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hw_driver


class crosChip(hw_driver.HwDriver):
  """Driver for getting chip name of EC or PD."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(crosChip, self).__init__(interface, params)
    self._interface = interface
    self._chip = self._params.get('chip', 'unknown')
    self._chip_for_ccd = self._params.get('chip_for_ccd', 'unknown')

  def _Get_chip(self):
    """Get the EC chip name."""
    if ('ccd_cr50' in self._interface._version.lower() and
        self._chip_for_ccd != 'unknown'):
      return self._chip_for_ccd

    return self._chip
