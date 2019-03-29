# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Provides a base class for I2C bus implementations."""

import logging
import os
import subprocess
import threading
import weakref

import i2c_pseudo


def _format_write_list(write_list):
  """Format a BaseI2CBus.wr_rd() write_list arg for logging.

  Args:
    write_list: list of output byte values [0~255], or None for no write

  Returns:
    str
  """
  if write_list is None:
    return str(None)
  return '[%s]' % (', '.join('0x%02X' % (value,) for value in write_list),)


class BaseI2CBus(object):
  """Base class for all I2c bus classes.

  Thread safety:
    All public methods are safe to invoke concurrently from multiple threads.

  Usage:
    class MyI2CBus(BaseI2CBus):
      def _raw_wr_rd(self, slave_address, write_list, read_count):
        # Implement hdctools wr_rd() interface here.
  """

  def __init__(self):
    """Initializer."""
    self.__logger = logging.getLogger('i2c_base')
    self.__lock = threading.Lock()
    self.__pseudo_adap = None
    self.reinit()

  # This exists to reinitialize the I2C pseudo controller after FTDI I2C
  # reinitialization, which is a hack supported for iteflash using Servo v2.
  def init(self):
    self.reinit()

  def reinit(self):
    with self.__lock:
      if self.__pseudo_adap is not None:
        self.__do_close()

      # While the I2C pseudo adapter controller itself does not need i2c-dev, it
      # is intended to be available for userspace processes, so for convenience
      # we make sure i2c-dev is loaded if available.
      self.__modprobe('i2c-dev', True)
      # The I2C pseudo adapter controller very much needs i2c-pseudo!
      self.__modprobe('i2c-pseudo', True)

      pseudo_ctrlr_path = i2c_pseudo.default_controller_path()
      if not os.path.exists(pseudo_ctrlr_path):
        self.__logger.info('path %r not found, not starting I2C pseudo adapter'
                           % (pseudo_ctrlr_path,))
        return
      # TODO(b/79684405): This circular reference is less than ideal.  Find a
      # better way to hook i2c_pseudo.I2cPseudoAdapter into servod.  For now
      # weakref is used to avoid a reference count cycle.
      self.__logger.info('path %r found, starting I2C pseudo adapter' %
                         (pseudo_ctrlr_path,))
      self.__pseudo_adap = i2c_pseudo.I2cPseudoAdapter(
          pseudo_ctrlr_path, weakref.proxy(self))
      self.__pseudo_adap.start()

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

    Returns:
      [None or [int]] - A list of .wr_rd() return values, one for each
          transaction.

          Each item is a list of the bytes read from one transaction.  If no
          bytes were read, the item may be an empty list, or may be None instead
          of a list.

          Instead of int, another type that represents and acts as an integer
          may be used, such as ctypes.c_ubyte.
    """
    with self.__lock:
      return [self._raw_wr_rd(*args) for args in transactions]

  def wr_rd(self, slave_address, write_list, read_count):
    """Implements hdctools wr_rd() interface.

    This function writes byte values list to I2C device (if given), then reads
    byte values from the same device (if requested).

    For a given I2C bus object, overlapping calls to this method will be
    serialized by means of a mutex or equivalent, thus while one call is
    executing, the rest will block.

    Args:
      slave_address: 7 bit I2C slave address.
      write_list: list of output byte values [0~255], or None for no write
      read_count: number of byte values to read from device, or None for no read

    Returns:
      None or [int] - A list of the bytes read.  If no bytes were read, either
          None or an empty list may be returned.  Instead of int, another type
          that represents and acts as an integer may be used, such as
          ctypes.c_ubyte.
    """
    with self.__lock:
      self.__logger.debug(
          'i2c_base.BaseI2CBus.wr_rd(0x%02X, %s, %s) called' %
          (slave_address, _format_write_list(write_list), read_count))
      retval = self._raw_wr_rd(slave_address, write_list, read_count)
      self.__logger.debug(
          'i2c_base.BaseI2CBus.wr_rd(0x%02X, %r, %s) returning %s' %
          (slave_address, _format_write_list(write_list), read_count, retval))
    return retval

  def _raw_wr_rd(self, slave_address, write_list, read_count):
    """Implements hdctools wr_rd() interface.

    This function writes byte values list to I2C device (if given), then reads
    byte values from the same device (if requested).

    For a given I2C bus object, there should never be overlapping calls to this
    method.  Implementations should therefore make no special effort to handle
    calls from multiple threads.

    Args:
      slave_address: 7 bit I2C slave address.
      write_list: list of output byte values [0~255], or None for no write
      read_count: number of byte values to read from device, or None for no read

    Returns:
      None or [int] - A list of the bytes read.  If no bytes were read, either
          None or an empty list may be returned.  Instead of int, another type
          that represents and acts as an integer may be used, such as
          ctypes.c_ubyte.
    """
    raise NotImplementedError

  def close(self):
    """Stop the I2C pseudo interface, if it was started."""
    with self.__lock:
      if self.__pseudo_adap is not None:
        self.__do_close()

  # self.__lock must be held and self.__pseudo_adap must not be None.
  def __do_close(self):
    self.__pseudo_adap.shutdown(2)
    # Break the circular reference.
    # TODO(b/79684405): This circular reference is less than ideal.  Find a
    # better way to fit i2c_pseudo.I2cPseudoAdapter into servod.
    self.__pseudo_adap = None

  def __modprobe(self, module, quiet):
    """Run modprobe for a given module name.

    Args:
      module: str - The module name to attempt to load.
      quiet: bool - Whether or not to ask modprobe to suppress error output.
        Regardless of the value of this setting, modprobe stdout and stderr will
        be inherited from servod.

    The modprobe attempt and its exit status will be logged at INFO level
    regardless of the quiet setting.
    """
    # Escape the CrOS development chroot to find modules for the host system.
    # Servod should be running as root anyways, should have permission for this.
    args = ['chroot', '--', '/proc/1/root', 'modprobe']
    if quiet:
      args.append('--quiet')
    args.append('--')
    args.append(module)
    logging.info('Executing command: %r' % (args,))
    ret = subprocess.call(args)
    logging.debug('Exit status was %d (negative is killed by signal) for '
                  'command: %r' % (ret, args))
    return ret
