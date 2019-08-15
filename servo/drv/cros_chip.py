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
    servo_type = interface._version
    devices = servo_type.split('with_')[-1].lower().split('_and_')
    default_device = devices[0]
    self._chips = {}
    for device in devices:
        self._chips[device] = self._params.get('chip_for_' + device,
                                               default_chip)
    self._chip = self._chips[default_device]
    self._check_active_device = ('servo_v4' in servo_type and
                                 len(devices) > 1)

  def _Get_chip(self):
    """Get the EC chip name."""
    if self._check_active_device:
        device = self._interface.get('active_v4_device')
        return self._chips[device]
    else:
        return self._chip
