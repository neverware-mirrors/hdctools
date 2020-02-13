# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for c2d2 specific controls through ec3po.
"""

import logging
import time

import ec3po_servo
import pty_driver
import servo


class ec3poC2d2Error(pty_driver.ptyError):
  """Exception class for c2d2 ec3po."""


class ec3poC2d2(ec3po_servo.ec3poServo):
  """Object to access drv=ec3po_c2d2 controls.

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
      ec3poC2d2Error: on init failure
    """
    ec3po_servo.ec3poServo.__init__(
        self, interface, params, board='c2d2')

    self._logger.debug('')

  def _Get_uut_boot_mode(self):
    """Gets the current UUT (UART) boot mode for the EC.

    Returns:
      'on' if EC_TX is being held low. The UART on stm32 is disabled
      'off' if EC_TX and EC_RX are in normal UART mode
    """
    # EC UART is connected to USART1
    result = self._issue_cmd_get_results('hold_usart usart1',
      ['status: (\w+)'])[0][1]
    if result == 'normal':
        return 'off'
    return 'on'

  def _Set_uut_boot_mode(self, value):
    """Sets the current UUT (UART) boot mode for the EC

    Args:
      value: 1 to hold EC_TX low, 0 to use EC UART as normal
    """
    # EC UART is connected to USART1
    self._issue_cmd('hold_usart usart1 %s' % value)

  def _Get_h1_reset(self):
    """Gets the current H1 reset state for DUT.

    Returns:
      'on' if H1 is being held in reset.
      'off' if H1 can run normally.
    """
    result = self._issue_cmd_get_results('h1_reset',
      ['H1 reset held: (\w+)'])[0][1]
    if result == 'yes':
        return 'on'
    return 'off'

  def _Set_h1_reset(self, value):
    """Sets the current H1 reset state for DUT.

    Args:
      value: 1 to hold H1 in reset, 0 to release H1 from reset.
    """
    self._issue_cmd('h1_reset %s' % value)

  def _Get_pwr_button(self):
    """Gets the current power button state for DUT.

    Returns:
      'on' if power button is being held in reset.
      'off' if power button is released
    """
    result = self._issue_cmd_get_results('pwr_button',
      ['Power button held: (\w+)'])[0][1]
    if result == 'yes':
        return 'on'
    return 'off'

  def _Set_pwr_button(self, value):
    """Sets the current power button state for DUT.

    Args:
      value: 1 to hold power button, 0 to release power button.
    """
    self._issue_cmd('pwr_button %s' % value)

  def _Get_spi_vref(self):
    """Gets the current SPI Vref for DUT voltage.

    Returns:
      Rail voltage in mV
    """
    result = self._issue_cmd_get_results('enable_spi',
      ['SPI Vref: (\d+)'])[0][1]
    return result

  def _Set_spi_vref(self, value):
    """Sets the current SPI Vref for DUT voltage.

    Args:
      value: 0, 1800, and 3300; The mV to the rail
    """
    self._issue_cmd('enable_spi %s' % value)

  def _Get_i2c_speed(self):
    """Gets the i2c bus speed for the bus specified in the control

    Returns:
      I2C Bus speed in kbps units
    """
    bus = self._params['bus']
    result = self._issue_cmd_get_results('enable_i2c %s' % bus,
      ['I2C speed kpbs: (\d+)'])[0][1]
    return result

  def _Set_i2c_speed(self, value):
    """Sets the i2c bus speed for the bus specified in the control.

    Args:
      value: 0, 100, and 400; The i2c bus speed in kpbs units
    """
    bus = self._params['bus']
    self._issue_cmd('enable_i2c %s %d' % (bus, value))
