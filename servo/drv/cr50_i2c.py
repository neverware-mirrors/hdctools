# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for CR50 I2C interface
   This is for the special-purpose commands that Cr50 can handle.
"""

import hw_driver

CMD_MASK=0xFF


class cr50I2cError(hw_driver.HwDriverError):
  """Error class for cr50I2c"""


class cr50I2c(hw_driver.HwDriver):
  """Object to access drv=pca9546 controls."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: interface object to handle low-level communication to control
      params: dictionary of params needed to perform operations on CR50

    Mandatory Params:
      slv: integer, 7-bit i2c slave address
    """
    super(cr50I2c, self).__init__(interface, params)
    self._logger.debug('')
    self._slave = int(self._params['slv'], 0)

  def set(self, value):
    """send a special command to CR50.

    Args:
      value: a special command in 8-bit unsigned integer

    Raises:
      cr50I2cError: if value is out of bounds
    """
    self._logger.debug('value = %r' % (value,))
    if value & ~CMD_MASK:
      raise cr50I2cError("command value 0x%X does not match 0x%X" %
                         (value, CMD_MASK))
    self._interface.wr_rd(self._slave, [value], 0)
