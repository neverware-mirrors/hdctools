# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver class for reading properties of a Servod I2C pseudo controller."""

import hw_driver


class i2cPseudo(hw_driver.HwDriver):
  """Class to access drv=i2c_pseudo controls."""

  def _Get_is_started(self):
    """Check if the I2C pseudo adapter has been started.

    Returns: bool
    """
    return self._interface.pseudo_adap is not None

  def _Get_is_running(self):
    """Check if the I2C pseudo adapter I/O thread is running.

    Returns: bool
    """
    pseudo_adap = self._interface.pseudo_adap
    return pseudo_adap is not None and pseudo_adap.is_running

  def _Get_i2c_adapter_num(self):
    """Get the I2C adapter number of this I2C pseudo adapter.

    Returns: None or int
    """
    pseudo_adap = self._interface.pseudo_adap
    return None if pseudo_adap is None else pseudo_adap.i2c_adapter_num

  def _Get_i2c_pseudo_id(self):
    """Get the I2C pseudo ID of this I2C pseudo adapter.

    Returns: None or int
    """
    pseudo_adap = self._interface.pseudo_adap
    return None if pseudo_adap is None else pseudo_adap.i2c_pseudo_id
