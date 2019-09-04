# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Fluffy Servo Driver"""

import logging
import pty_driver

ACTIVE_PORT_RX_RE = r'Port (\d+) is ON'
NO_PORT_RX = r'No ports enabled'
CC_FLIP_RE = r'CC Flip: (\w+)\]'
DUT_VOLTAGE_RE = r'PPVAR_VBUS_DUT: (\d+)mV'

class fluffy(pty_driver.ptyDriver):
  """Object to control fluffy debug board"""

  def __init__(self, interface, params, board=''):
    """Constructor.

      Args:
      interface: interface object to handle low-level communication to
        control
      params: dictionary of params needed
    """
    super(fluffy, self).__init__(interface, params)
    self._board = board

  def _Get_active_chg_port(self):
    """Getter of the active charge port.

    Returns:
      A string of the active charge port.
    """
    result = self._issue_cmd_get_results('status', [ACTIVE_PORT_RX_RE + r'|' +
                                                    NO_PORT_RX])[0]
    self._logger.debug('result: %r', result)
    if (result == NO_PORT_RX):
      return result

    # If it's not just a string, it's a tuple with the match of the active
    # charge port.
    _, active_port = result
    return active_port

  def _Set_active_chg_port(self, port):
    """Sets the desired active charge port.

    Args:
    port: A string indicating the desired active charge port, or 'off'.
    """
    if port.lower() == 'off':
        # The port number doesn't matter if you're turning off a port.
        self._issue_cmd_get_results('port 0 off', [NO_PORT_RX])
        return

    # For some reason, it doesn't take effect unless _issue_cmd_get_results is
    # used.
    self._issue_cmd_get_results('port %d on' % (int(port)),
                                [ACTIVE_PORT_RX_RE])

  def _Get_cc_flip_en(self):
    """Getter of the CC flip setting.

    Returns:
      A string ('on' or 'off') indicating whether CC flip is enabled.
    """
    result = self._issue_cmd_get_results('status', [CC_FLIP_RE])[0]
    _, enable = result
    return 'on' if enable.lower() == 'yes' else 'off'

  def _Set_cc_flip_en(self, enable):
    """Setter of the CC flip setting.

    Args:
    enable: An integer (0 or 1), indicating the desired setting for the CC flip
      feature.
    """
    val = 'enable' if enable else 'disable'
    self._issue_cmd_get_results('ccflip %s' % val, [CC_FLIP_RE])

  def _Get_dut_voltage(self):
    """Getter of the voltage present at the DUT connector.

    Returns:
      A string indicating the voltage present at the DUT connector in mV.
    """
    _, voltage = self._issue_cmd_get_results('status', [DUT_VOLTAGE_RE])[0]
    return voltage
