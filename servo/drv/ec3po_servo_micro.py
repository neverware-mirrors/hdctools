# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servo micro specific controls through ec3po.

Provides the following console controlled function subtypes:
  usbpd_console
"""

import re
import logging
import time

import ec3po_servo
import pty_driver
import servo

# Controls to set in batch operations.
# [off, samus, glados]
usbpd_uart_config = {
    'UART3_RX_JTAG_BUFFER_TO_SERVO_TDO': ('IN', 'ALT', 'ALT'),
    'UART3_TX_SERVO_JTAG_TCK': ('IN', 'ALT', 'ALT'),
    'SPI1_MUX_SEL': ('1', '0', '1'),
    'SPI1_BUF_EN_L': ('1', '0', '1'),
    'SPI1_VREF_18': ('0', '1', '0'),
    'SPI1_VREF_33': ('0', '0', '0'),
    'JTAG_BUFIN_EN_L': ('1', '1', '0'),
    'SERVO_JTAG_TDO_BUFFER_EN': ('0', '0', '1'),
    'SERVO_JTAG_TDO_SEL': ('0', '0', '1'),
}
# Time in seconds to wait for console readiness after a UART routing switch.
# This value was determined experimentally.
CONSOLE_READINESS_DELAY = 0.5

class ec3poServoMicroError(pty_driver.ptyError):
  """Exception class for ec."""


def _GetIteChipidReStr(command):
  """Get a regexp for matching get_ite_chipid Servo console command output.

  Args:
    command: str - The actual console command that will be run.  This should
        either be 'get_ite_chipid' itself or another command with identical
        output.

  Returns:
    str - A regexp that will match either the expected output, or the usage
        output, because the latter is typically printed after any error message.
        Match group 1 will contain the output either way.  If it starts with
        'Usage:' then an error occurred.

  This returns str instead of re.compile() because that is what the
  pty_driver.ptyDriver._issue_cmd_get_results() interface accepts.
  """
  return (
      # Match the beginning of a line.
      r'[\r\n\f]('
      # Match the expected output.
      r'ITE EC info:[^\r\n\f]*'
      # Alternatively, match the usage output, because it is typically printed
      # after any error message.  This avoids waiting for the Servod pexpect
      # timeout after typical errors.
      r'|Usage: %s(?:[ \t\v]+[^\r\n\f]*)?'
      # Match the end of a line.
      r')[\r\n\f]' % (re.escape(command),))


class ec3poServoMicro(ec3po_servo.ec3poServo):
  """Object to access drv=ec3po_servo_micro controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read kbd_en would be dispatched to
  call _Get_kbd_en.
  """

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: ec3po interface object to handle low-level communication to
        control
      params: dictionary of params needed
    Raises:
      ec3poServoMicroError: on init failure
    """
    ec3po_servo.ec3poServo.__init__(
        self, interface, params, board='servo_micro')

    self._logger.debug('')

  def _Get_uut_boot_mode(self):
    """Gets the current UUT (UART) boot mode for the EC.

    Returns:
      'on' if EC_TX is being held low. The UART on stm32 is disabled
      'off' if EC_TX and EC_RX are in normal UART mode
    """
    # EC UART is connected to USART2
    result = self._issue_cmd_get_results('hold_usart usart2',
      ['status: (\w+)'])[0][1]
    if result == 'normal':
        return 'off'
    return 'on'

  def _Set_uut_boot_mode(self, value):
    """Sets the current UUT (UART) boot mode for the EC

    Args:
      value: 1 to hold EC_TX low, 0 to use EC UART as normal
    """
    # EC UART is connected to USART2
    self._issue_cmd('hold_usart usart2 %s' % value)

  def batch_set(self, batch, index):
    """Set a batch of values on servo micro.

    Args:
      batch: dict of GPIO names, and on/off value
      index: index of batch preset
    """
    if index not in [0, 1, 2]:
      raise ec3poServoMicroError('Index (%s) must be 0, 1, or 2' % index)

    for name, values in batch.items():
      cmd = 'gpioset %s %s\r' % (name, values[index])
      self._issue_cmd(cmd)

  def _Set_usbpd_console(self, value):
    """Set or unset PD console routing

    Args:
      value: An integer value, 0: none, 1:samus, 2:glados
    """
    self.batch_set(usbpd_uart_config, value)
    # Add a short delay, so the console will be accessible immediately after the
    # control is set.
    time.sleep(CONSOLE_READINESS_DELAY)

  def _Get_usbpd_console(self):
    """Set or unset PD console routing

    Args:
      value: An integer value, 0: none, 1:samus, 2:glados
    """
    return 0

  def _Get_enable_ite_dfu(self):
    """Enable ITE EC direct firmware update over I2C mode.

    Enable direct firmware update (DFU) over I2C mode on ITE IT8320 EC chip by
    sending special non-I2C waveforms over the I2C bus wires.
    """
    results = self._issue_safe_cmd_get_results('enable_ite_dfu', [
        _GetIteChipidReStr('enable_ite_dfu')])
    if results[0] is None or results[0][1].startswith('Usage:'):
      raise ec3poServoMicroError(
          'Failed to enable DFU mode.  results=%r' % (results,))
    return results[0][1].strip()

  def _Get_get_ite_chipid(self):
    """Verify that ITE EC chip is in DFU mode by querying for its chip ID.

    Verify that ITE IT8320 EC chip direct firmware update (DFU) mode is enabled
    by querying the EC over I2C for its CHIPID1 and CHIPID2 registers.  It will
    only respond over I2C when in DFU mode.
    """
    results = self._issue_safe_cmd_get_results('get_ite_chipid', [
        _GetIteChipidReStr('get_ite_chipid')])
    if results[0] is None or results[0][1].startswith('Usage:'):
      raise ec3poServoMicroError(
          'Failed to query ITE EC chip ID, or failed to parse the output.  Has '
          'enable_ite_dfu been called?  results=%r' % (results,))
    return results[0][1].strip()
