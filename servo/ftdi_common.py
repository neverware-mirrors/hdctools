# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines common structures for use with c libraries related to FTDI devices.
"""
import ctypes
from collections import OrderedDict

import servo_interfaces


MAX_FTDI_INTERFACES_PER_DEVICE = 4

(DEFAULT_VID, DEFAULT_PID) = servo_interfaces.SERVO_ID_DEFAULTS[0]

(INTERFACE_TYPE_ANY, INTERFACE_TYPE_GPIO, INTERFACE_TYPE_I2C,
 INTERFACE_TYPE_JTAG, INTERFACE_TYPE_SPI, INTERFACE_TYPE_UART) = \
 map(ctypes.c_int, xrange(6))

# key == <board>_<version>
# value == list of lot identifiers (lot_id)
SERVO_LOT_ID_DEFAULTS = \
    {'miniservo_v1': ['001', '540052'],
     'servo_v1': ['483881', '498432'],
     'servo_v2_r0': ['609600', '629871'],
     'servo_v2': ['641220', '686203', '730422', '780735', '868534', '875286']
     }

SERVO_PID_DEFAULTS = OrderedDict([
    ('miniservo_v1', [0x5000]),
    ('servo_v1', [0x5001]),
    ('servo_v2', [0x5002]),
    ('servo_v3', [0x5004, 0x6014]),
    ('servo_v4', [0x501b]),
    ('servo_micro', [0x501a]), # should be below servo_v4
    ('ccd_cr50', [0x5014]), # should be below servo_v4
    ('toad_v1', [0x6015]), # Vendor ID is 0x403 : FTDI
    ('reston', [0x5007]),
    ('fruitpie', [0x5009]),
    ('plankton', [0x500c])])

SERVO_CONFIG_DEFAULTS = \
    {'miniservo_v1': ['miniservo.xml'],
     'servo_v1': ['servo.xml'],
     'servo_v2_r0': ['servo_v2_r0.xml'],
     'servo_v2': ['servo_v2_r1.xml'],
     'servo_v3': ['servo_v3_r0.xml'],
     'servo_v4': ['servo_v4.xml'],
     'servo_micro': ['servo_micro.xml'],
     'ccd_cr50': ['ccd_cr50.xml'],
     'toad_v1': ['toad.xml'],
     'reston': ['reston.xml'],
     'fruitpie': ['fruitpie.xml'],
     'plankton': ['plankton.xml'],
     }

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
    ('asynctypes.c_usb_buffer_size', ctypes.c_uint),
    ('module_detach_mode', ctypes.c_int)]

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
