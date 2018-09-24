# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Texas Instruments INA231 on sweetberry."""

import copy
import ina231

import hw_driver

class sweetberryError(hw_driver.HwDriverError):
  pass

class sweetberry(ina231.ina231):
  """wrapper class around ina231 for sweetberry.

  Sweetberry i2c has 4 ports (0,1,2,3) it uses to read INAs. This wrapper
  around ina231 allows to read the right port by making copies of the
  i2c interface object and replacing the port with the appropiate port
  for the control.

  Note: copy.copy does not copy the underlying usb interface, but rather
        creates different objects that use the same usb interface but
        execute i2c commands with different ports.

  Attributes:
    _interfaces: Cache for controls that share i2c port to use the same
                 interface index is the port, and content is an i2c interface
                 with that port.
  """

  _interfaces = [None, None, None, None]

  def __init__(self, interface, params):
    """Initialize i2c driver by determining & setting up port.
    Args:
      interface: i2c driver, in this case stm32i2c as it's sweetberry
      params: params used for i2c transaction. 'port' attribute is read
              as the i2c port.
    """
    try:
      port = int(params['port'])
    except KeyError:
      raise sweetberryError("Sweetberry INAs need to define their port.")
    if port > 3 or port < 0:
      raise sweetberryError("Port value: %d invalid for sweetberry" % port)
    if not sweetberry._interfaces[port]:
      sweetberry._interfaces[port] = copy.copy(interface)
      sweetberry._interfaces[port]._port = port
    iface = sweetberry._interfaces[port]
    super(sweetberry, self).__init__(iface, params)
