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
    default_chip = self._params.get('chip', 'unknown')
    flashing_device = interface._version.split('with_')[-1].lower()
    self._chip = self._params.get('chip_for_' + flashing_device, default_chip)

  def _Get_chip(self):
    """Get the EC chip name."""
    return self._chip
