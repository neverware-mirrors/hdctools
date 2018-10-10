# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Provides a base class for I2C bus implementations."""

import threading


class BaseI2CBus(object):
  """Base class for all I2c bus classes.

  Usage:
    class MyI2CBus(BaseI2CBus):
      def _raw_wr_rd(self, slave_address, write_list, read_count):
        # Implement hdctools wr_rd() interface here.
  """

  def __init__(self):
    """Initializer."""
    self.__lock = threading.Lock()

  def multi_wr_rd(self, transactions):
    """Allows for multiple write/read/write+read I2C transactions.

    This guarantees that no other I2C messages/transactions are sent by this
    object in the middle of the transactions passed to this function.

    This does NOT combine the transactions passed to this function into one I2C
    transaction.

    Args:
      transactions: iterable of (slave_address, write_list, read_count) tuples
        slave_address: 7 bit I2C slave address.
        write_list: list of output byte values [0~255], or None for no write
        read_count: number of byte values to read from device, or None for no
            read
    """
    with self.__lock:
      return [self._raw_wr_rd(*args) for args in transactions]

  def wr_rd(self, slave_address, write_list, read_count):
    """Implements hdctools wr_rd() interface.

    This function writes byte values list to I2C device (if given), then reads
    byte values from the same device (if requested).

    Args:
      slave_address: 7 bit I2C slave address.
      write_list: list of output byte values [0~255], or None for no write
      read_count: number of byte values to read from device, or None for no read

    For a given I2C bus object, overlapping calls to this method will be
    serialized by means of a mutex or equivalent, thus while one call is
    executing, the rest will block.
    """
    with self.__lock:
      return self._raw_wr_rd(slave_address, write_list, read_count)

  def _raw_wr_rd(self, slave_address, write_list, read_count):
    """Implements hdctools wr_rd() interface.

    This function writes byte values list to I2C device (if given), then reads
    byte values from the same device (if requested).

    Args:
      slave_address: 7 bit I2C slave address.
      write_list: list of output byte values [0~255], or None for no write
      read_count: number of byte values to read from device, or None for no read

    For a given I2C bus object, there will never be overlapping calls to this
    method.  Implementations should therefore make no special effort to handle
    calls from multiple threads.
    """
    raise NotImplementedError
