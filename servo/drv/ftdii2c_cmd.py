# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to execute some control commands directly on ftdii2c.

See ftdii2c.py for details on controls available.
"""

import hw_driver


# pylint: disable=C0103
class ftdii2cCmdError(hw_driver.HwDriverError):
  """Exception class for ftdii2c_cmd."""


class ftdii2cCmd(hw_driver.HwDriver):
  """Object to access drv=ftdii2c_cmd controls.

  Attributes:
    _ftdii2c: ftdi i2c object to execute commands on

  """

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: servod instance to get a hold of the ftdii2c object
      params: dictionary of params needed to perform operations on
        devices.
    """
    # pylint: disable=protected-access
    super(ftdii2cCmd, self).__init__(interface, params)
    self._logger.debug('')
    try:
      index = interface._interfaces.index('ftdi_i2c')
    except ValueError:
      raise ftdii2cCmdError('No ftdi_i2c object found.')
    self._ftdii2c = interface._interface_list[index]

  def set(self, cmd):
    """Execute |cmd| on |self._ftdii2c| object.

    Args:
      cmd: str representing the ftdi i2c command to execute
    """
    try:
      func = getattr(self._ftdii2c, cmd)
    except AttributeError:
      raise ftdii2cCmdError('ftdi_i2c object does not have method %r' % cmd)
    self._logger.debug('Running %s on ftdii2c interface.', cmd)
    func()

  def get(self):
    """Raise error as a command needs to be specified."""
    raise ftdii2cCmdError('No cmd specified for ftdii2c_cmd')
