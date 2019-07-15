# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Accesses I2C buses through stm32 usb endpoint."""

import array
import errno
import logging
import usb

import i2c_base
import stm32usb

_MAX_WRITE_SIZE = (1 << 12) - 1
_MAX_READ_SIZE = (1 << 15) - 1


class Si2cError(Exception):
  """Class for exceptions of Si2c."""

  def __init__(self, msg, value=0):
    """Si2cError constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(Si2cError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class Si2cBus(i2c_base.BaseI2CBus):
  """I2C bus class to access devices on the bus.

  Usage:
    bus = Si2cBus()
    # read 1 byte from slave(0x48) register(0x16)
    bus.wr_rd(0x48, [0x16], 1)
    # write 2 bytes to slave(0x48) register(0x20)
    bus.wr_rd(0x48, [0x20, 0x01, 0x02])

  Instance Variables:
    _logger: Si2c tagged log output
    _port: stm32 i2c controller index
    _susb: stm32 usb class
  """

  def __init__(self, vendor=0x18d1, product=0x501a, interface=1, port=0,
               serialname=None):
    i2c_base.BaseI2CBus.__init__(self)

    self._logger = logging.getLogger('Si2c')
    self._logger.debug('')

    self._port = port
    self._logger.debug('Set port %d' % port)

    self._susb = stm32usb.Susb(vendor=vendor, product=product,
                               interface=interface, serialname=serialname,
                               logger=self._logger)

    self._logger.debug('Set up stm32 i2c')

  def reinitialize(self):
    """Reinitialize the usb endpoint"""
    self._susb.reset_usb()

  def get_device_info(self):
    """The usb device information."""
    return self._susb.get_device_info()

  def _raw_wr_rd(self, slave_address, write_list, read_count=None):
    """Implements hdctools wr_rd() interface.

    This function writes byte values list to I2C device, then reads
    byte values from the same device.

    Args:
      slave_address: 7 bit I2C slave address.
      write_list: list of output byte values [0~255].
      read_count: number of byte values to read from device.

    Interface:
      write: [addr, write_count, read_count, data ... ]
      read: [data .. ]

    Returns:
      Bytes read from i2c.

    Raises:
      Si2cError on transaction failure.
    """
    self._logger.debug(
        'Si2c.wr_rd('
        'port=%d, slave_address=0x%x, write_list=%s, read_count=%s)' %
        (self._port, slave_address, write_list, read_count))

    # Clean up args from python style to correct types.
    if not write_list:
      write_list = []
    write_length = len(write_list)
    if write_length > _MAX_WRITE_SIZE:
      raise Si2cError(
          'requested write size %d exceeds the %d maximum supported by this '
          'I2C-over-USB protocol' % (write_length, _MAX_WRITE_SIZE))

    read_count = max(0, read_count)
    if read_count > _MAX_READ_SIZE:
      raise Si2cError(
          'requested read size %d exceeds the %d maximum supported by this '
          'I2C-over-USB protocol' % (read_count, _MAX_READ_SIZE))

    # Encode the full write count across the multiple fields involved.
    port_field = self._port | ((write_length >> 4) & 0xF0)
    write_field = write_length & 0xFF
    cmd = [port_field, slave_address, write_field]

    # Encode the full read count across the multiple fields involved.
    if read_count <= 0x7F:
      cmd.append(read_count)
    else:
      cmd.append((read_count & 0x7F) | 0x80)
      cmd.append((read_count >> 7) & 0xFF)
      cmd.append(0)  # reserved field

    # Send wr_rd command to stm32.
    cmd.extend(write_list)
    try:
      ret = self._susb._write_ep.write(cmd, self._susb.TIMEOUT_MS)
    except IOError as e:
      if e.errno == errno.ENODEV:
        self._logger.error('USB disconnected 0x%04x:%04x, servod failed.',
            self._susb._vendor, self._susb._product)
      raise

    # Read back response if necessary.
    data = self._susb._read_ep.read(read_count + 4, self._susb.TIMEOUT_MS)

    if len(data) < (read_count + 4):
      raise Si2cError('Read status failed.')

    if data[0] != 0 or data[1] != 0:
      raise Si2cError('Read status failed: 0x%02x%02x' % (data[1], data[0]))

    self._logger.debug('Si2c.wr_rd result 0x%02x%02x, read %s' %
                       (data[1], data[0], data[4:]))
    return data[4:]

  def close(self):
    """Stm32i2c wind down logic.

    Note: because servod runs in a thread, an exception gets thrown at the very
    end unless we explicitly predelete this instance.
    """
    self._logger.info('Turning down STM32i2c interface.')
    del self._susb
    super(Si2cBus, self).close()
