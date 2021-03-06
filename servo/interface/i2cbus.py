# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Accesses I2C buses through Linux i2c-dev driver."""

import fcntl
import io

import i2c_base


class I2CBus(i2c_base.BaseI2CBus):
  """I2C bus class to access devices on the bus.

  Usage:
    bus = I2CBus('/dev/i2c-0')
    # read 1 byte from child(0x48) register(0x16)
    bus.wr_rd(0x48, [0x16], 1)
    # write 2 bytes to child(0x48) register(0x20)
    bus.wr_rd(0x48, [0x20, 0x01, 0x02])
  """
  _I2C_SLAVE_FORCE = 0x0706

  def __init__(self, interface):
    i2c_base.BaseI2CBus.__init__(self)
    self._interface = interface

  @staticmethod
  def Build(interface_data, **kwargs):
    """Factory method to implement the interface."""
    return I2CBus('/dev/i2c-%d' % interface_data['bus_num'])

  @staticmethod
  def name():
    """Name to request interface by in interface config maps."""
    return 'dev_i2c'

  def _raw_wr_rd(self, child_address, write_list, read_count=None):
    """Implements hdctools wr_rd() interface.

    This function writes byte values list to I2C device, then reads
    byte values from the same device.

    Args:
      child_address: 7 bit I2C child address.
      write_list: list of output byte values [0~255].
      read_count: number of byte values to read from device.
    """
    bus = io.open(self._interface, mode='r+b', buffering=0)
    fcntl.ioctl(bus.fileno(), self._I2C_SLAVE_FORCE, child_address)
    if write_list:
      output_buf = ''.join(chr(byte_value) for byte_value in write_list)
      bus.write(output_buf)
    if read_count:
      return [ord(byte) for byte in bus.read(read_count)]
