# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines common structures for use with c libraries related to FTDI devices.
"""
import ctypes
import collections

SERVO_ID_DEFAULTS = [(0x0403, 0x6011), (0x18d1, 0x5001)]
(DEFAULT_VID, DEFAULT_PID) = SERVO_ID_DEFAULTS[0]

INTERFACE_DEFAULTS = collections.defaultdict(dict)
for vid, pid in SERVO_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['gpio', 'i2c', 'uart', 'gpio']

# miniservo
MINISERVO_ID_DEFAULTS = [(0x403, 0x6001), (0x18d1, 0x5000)]
for vid, pid in MINISERVO_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = ['gpiouart']

SERVO_ID_DEFAULTS.extend(MINISERVO_ID_DEFAULTS)

(INTERFACE_TYPE_ANY, INTERFACE_TYPE_GPIO, INTERFACE_TYPE_I2C,
 INTERFACE_TYPE_JTAG, INTERFACE_TYPE_SPI, INTERFACE_TYPE_UART) = \
 map(ctypes.c_int, xrange(6))

class FtdiContext(ctypes.Structure):
  """Defines primary context structure for libftdi.

  Declared in ftdi.h with name ftdi_context.
  """
  _fields_ = [
    # USB specific
    ('usb_dev', ctypes.POINTER(ctypes.c_int)),
    ('usb_read_timeout', ctypes.c_int),
    ('usb_write_timeout', ctypes.c_int),
    # FTDI specific
    ('type', ctypes.c_int),
    ('baudrate', ctypes.c_int),
    ('bitbang_enabled', ctypes.c_ubyte),
    ('readbuffer', ctypes.POINTER(ctypes.c_ubyte)),
    ('readbuffer_offset', ctypes.c_uint),
    ('readbuffer_remaining', ctypes.c_uint),
    ('readbuffer_chunksize', ctypes.c_uint),
    ('writebuffer_chunksize', ctypes.c_uint),
    ('max_packet_size', ctypes.c_uint),
    # for FTx232 chips
    ('interface', ctypes.c_int),
    ('index', ctypes.c_int),
    # Endpoints
    ('in_ep', ctypes.c_int),
    ('out_ep', ctypes.c_int),
    ('bitbang_mode', ctypes.c_ubyte),
    ('eeprom_size', ctypes.c_int),
    ('error_str', ctypes.POINTER(ctypes.c_char)),
    ('asynctypes.c_usb_buffer', ctypes.POINTER(ctypes.c_char)),
    ('asynctypes.c_usb_buffer_size', ctypes.c_uint)]

class FtdiCommonArgs(ctypes.Structure):
  """Defines structure of common arguments for FTDI related devices.

  Declared in ftdi_common.h with name ftdi_common_args.
              ("serialname", ctypes.POINTER(ctypes.c_char)),
  """
  _fields_ = [("vendor_id", ctypes.c_uint),
              ("product_id", ctypes.c_uint),
              ("dev_id", ctypes.c_uint),
              ("interface", ctypes.c_int),
              ("serialname", ctypes.c_char_p),
              ("speed", ctypes.c_uint),
              ("bits", ctypes.c_int),
              ("parity", ctypes.c_int),
              ("sbits", ctypes.c_int),
              ("direction,", ctypes.c_ubyte),
              ("value", ctypes.c_ubyte)]

class Gpio(ctypes.Structure):
  """Defines structure for managing typical 8-bit GPIO used in FTDI devices.

  Declared in ftdi_common.h with name gpio_s
  """
  _fields_ = [("value", ctypes.c_ubyte),
              ("direction", ctypes.c_ubyte),
              ("mask", ctypes.c_ubyte)]
