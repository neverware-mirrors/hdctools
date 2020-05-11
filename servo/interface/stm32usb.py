# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allows creation of an interface via stm32 usb."""
import threading
import time

import common as c
import usb


class SusbError(c.InterfaceError):
  """Class for exceptions of Susb."""
  pass


class Susb():
  """Provide stm32 USB functionality.

  Instance Variables:
  _logger: S.* tagged log output
  _dev: pyUSB device object
  _read_ep: pyUSB read endpoint for this interface
  _write_ep: pyUSB write endpoint for this interface
  """
  READ_ENDPOINT = 0x81
  WRITE_ENDPOINT = 0x1
  TIMEOUT_MS = 100

  # The time after which to throw arms up when the lock acquisition fails.
  LOCK_TIMEOUT_S = 60
  # The rate to sample the lock at.
  LOCK_SAMPLING_RATE_S = 0.001

  def __init__(self, vendor=0x18d1, product=0x500f, interface=1,
               serialname=None, logger=None):
    """Susb constructor.

    Disconvers and connects to stm32 USB endpoints.

    Args:
      vendor    : usb vendor id of stm32 device
      product   : usb product id of stm32 device
      interface : interface number ( 1 - 4 ) of stm32 device to use
      serialname: string of device serialname.

    Raises:
      SusbError: An error accessing Susb object
    """
    if not logger:
      raise SusbError('No logger defined')
    self._logger = logger
    self._logger.debug('')
    # An event used to signal when a thread is trying to reinitialize the
    # interface.
    self._reset_done = threading.Event()
    # Only clear the flag when performing a reset.
    self._reset_done.set()
    # Setting up the read and write locks. These are per instance, as each
    # instance represents one interface.
    self._read_ep_lock = threading.Lock()
    self._write_ep_lock = threading.Lock()
    self._logger.debug('Set up stm32 read and write locks')


    self._vendor = vendor
    self._product = product
    self._interface = interface
    self._serialname = serialname
    self._dev = None
    self._find_device()

  def wait_on_reset(self):
    """Potentially give the resetting thread preference.

    When endpoints are being read in a (tight) loop like in the UART interfaces,
    a rice might happen between the reinitialization thread and the UART threads
    the reinitialization thread keeps losing out on the lock.

    With this helper, the thread can indicate that a reinit is about to happen,
    encouraging other threads that are performing read/write to stop asking for
    the lock, and wait until reinit is done.
    """
    # Set a very generous timeout for resetting to complete i.e the timeout
    # acquire both locks slowly, and one more lock timeout as buffer.
    if not self._reset_done.wait(3*self.LOCK_TIMEOUT_S):
      raise SusbError('Reset seems to have never finished for %04x:%04x %s' %
                      self.get_device_info())

  def reset_usb(self):
    """Reinitializes USB based on the device based settings from __init__"""
    # Signal that resetting is about to happen.
    self._reset_done.clear()
    # Reading and writing is unavailable until the reset has finished.
    self._acquire_lock(self._read_ep_lock, 'read ep')
    self._acquire_lock(self._write_ep_lock, 'write ep')
    try:
      self._find_device()
    except:
      self._logger.info('device not found: %04x:%04x %s',
                        *self.get_device_info())
    finally:
      self._write_ep_lock.release()
      self._read_ep_lock.release()
    # Signal that resetting is about to happen.
    self._reset_done.set()

  def get_device_info(self):
    """Returns a tuple (vid, pid, serialname)."""
    return (self._vendor, self._product, self._serialname)

  def _find_device(self):
    """Set up the usb endpoint"""
    # Find the stm32.
    dev_gen = usb.core.find(idVendor=self._vendor, idProduct=self._product,
                             find_all=True)
    dev_list = list(dev_gen)
    if dev_list is None or len(dev_list) is 0:
      raise SusbError('USB device not found')

    # Check if we have multiple stm32s and we've specified the serial.
    dev = None
    if len(dev_list) > 1 and self._serialname is not None:
      for d in dev_list:
        if usb.util.get_string(d, d.iSerialNumber) == self._serialname:
          dev = d
          break
      if dev is None:
        raise SusbError('USB device(%s) not found' % self._serialname)
    else:
      dev = dev_list[0]

    # TODO(crbug.com/1014672): investigate whether there is a better way not to
    # leak this many file descriptors for once system, and if there is a better
    # way to clean up the resources than the way/workaround implemented here.
    if self._dev:
      if self._dev.address != dev.address:
        # Dispose of the resources of the previously found device.
        usb.util.dispose_resources(self._dev)
      else:
        # The device did not reenumerate. No need to reinitialize it, it's still
        # valid.
        return

    # Detatch raiden.ko if it is loaded.
    if dev.is_kernel_driver_active(self._interface):
      dev.detach_kernel_driver(self._interface)
    usb.util.claim_interface(dev, self._interface)

    serial = '(%s)' % self._serialname if self._serialname else ''
    self._logger.debug('Found stm32%s: %04x:%04x' % (serial, self._vendor,
                                                     self._product))
    # If we can't set configuration, it's already been set.
    try:
      dev.set_configuration()
    except usb.core.USBError:
      pass
    self._dev = dev

    # Get an endpoint instance.
    try:
      cfg = dev.get_active_configuration()
    except usb.core.USBError as e:
      self._logger.error("")
      self._logger.error("ERROR: You may have run out of endpoints on your "
          "machine")
      self._logger.error("due to running too many servos simultaneously."
          " See crbug.com/652373")
      self._logger.error("")
      raise
    intf = usb.util.find_descriptor(cfg, bInterfaceNumber=self._interface)
    self._intf = intf

    self._logger.debug('InterfaceNumber: %s' % intf.bInterfaceNumber)

    read_ep_number = intf.bInterfaceNumber + self.READ_ENDPOINT
    read_ep = usb.util.find_descriptor(intf, bEndpointAddress=read_ep_number)
    self._read_ep = read_ep
    self._logger.debug('Reader endpoint: 0x%x' % read_ep.bEndpointAddress)

    write_ep_number = intf.bInterfaceNumber + self.WRITE_ENDPOINT
    write_ep = usb.util.find_descriptor(intf, bEndpointAddress=write_ep_number)
    self._write_ep = write_ep
    self._logger.debug('Writer endpoint: 0x%x' % write_ep.bEndpointAddress)

    self._logger.debug('Set up stm32 usb')

  def _acquire_lock(self, lock, name):
    """Try to acquire the |lock| within |LOCK_TIMEOUT_S|.

    Args:
      lock: lock to acquire
      name: name of the lock to log

    Raises:
      SinterfaceError: if |lock| cannot be acquired in |LOCK_TIMEOUT_S| s
    """
    end = time.time() + self.LOCK_TIMEOUT_S
    while time.time() < end:
      if lock.acquire(False):
        break
      time.sleep(self.LOCK_SAMPLING_RATE_S)
    else:
      # Acquisition failed. Report and raise an error.
      self._logger.error('%s lock acquisition failed after %ds.',
                         name, self.LOCK_TIMEOUT_S)
      raise SinterfaceError('Failed to acquire %s lock.' % name)

  def read_ep(self, *args, **kwargs):
    """Thread safe wrapper around reading the |read_ep|"""
    self.wait_on_reset()
    self._acquire_lock(self._read_ep_lock, 'read ep')
    try:
      return self._read_ep.read(*args, **kwargs)
    finally:
      self._read_ep_lock.release()

  def write_ep(self, *args, **kwargs):
    """Thread safe wrapper around writing to the |write_ep|"""
    self.wait_on_reset()
    self._acquire_lock(self._write_ep_lock, 'write ep')
    try:
      self._write_ep.write(*args, **kwargs)
    finally:
      self._write_ep_lock.release()

  def control(self, request, value):
    """Send control transfer.

    Args:
      request: the request type to send, bmRequestType
      data: the data to send, wValue

    Returns:
      boolean success/fail
    """
    # usb_setup_packet: ec/include/usb_descriptor.h:231
    reqtype = (
        usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR
        | usb.util.CTRL_RECIPIENT_INTERFACE)
    ret = self._dev.ctrl_transfer(bmRequestType=reqtype, bRequest=request,
                                  wIndex=self._interface, wValue=value)
    return True

  def __del__(self):
    """Sgpio destructor."""
    self._logger.debug('Close')
