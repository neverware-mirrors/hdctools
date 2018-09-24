# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for Parade PS8742 USB mux.."""

import hw_driver
import i2c_reg


class Ps8742Error(hw_driver.HwDriverError):
  """Error occurred accessing ps8742."""


class ps8742(hw_driver.HwDriver):
  """Object to access drv=ps8742 controls."""

  # I2C Addr of typical ps8742.
  USB_MUX_ADDR = 0x20
  # Control reg offset.
  USB_MUX_CTRL = 0
  # USB3 line passthough enable.
  USB_MUX_CTRL_USB3_EN = 0x20

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: i2c interface object to handle low-level communication to
          control
      params: dictionary of params needed to perform operations on this
          i2c device. All items are strings initially but should be cast to
          types detailed below.

    Mandatory Params:
      slv: integer, 7-bit i2c slave address
      offset: integer, gpio's bit position from lsb
    Optional Params:
    """
    super(ps8742, self).__init__(interface, params)
    slave = self._get_slave()
    self._i2c_obj = i2c_reg.I2cReg.get_device(
        self._interface, slave, addr_len=1, reg_len=1, msb_first=True,
        no_read=False, use_reg_cache=False)

  def _Get_usb3(self):
    """Getter for usb3 enable.

    Returns:
      0: USB2 only.
      1: USB3.
    """
    value = self._i2c_obj._read_reg(self.USB_MUX_CTRL)
    if self.USB_MUX_CTRL_USB3_EN & value:
      return 1
    return 0

  def _Set_usb3(self, enable):
    """Setter for usb3 enable.

    Args:
      enable: 0 - USB2 only. 1 - enable USB3.
    """
    value = self._i2c_obj._read_reg(self.USB_MUX_CTRL)
    if not enable:
      value = value & ~(self.USB_MUX_CTRL_USB3_EN)
    else:
      value = value | self.USB_MUX_CTRL_USB3_EN
    self._i2c_obj._write_reg(self.USB_MUX_CTRL, value)

  def _get_slave(self):
    """Check and return needed params to call driver.

    Returns:
      slave: 7-bit i2c address
    """
    if 'slv' not in self._params:
      raise Ps8742Error('getting slave address')
    slave = int(self._params['slv'], 0)
    return slave
