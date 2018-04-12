# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of drv=cr50.

Provides the following Cr50 controlled function:
  cold_reset
  warm_reset
  ccd_keepalive_en
"""

import functools
import logging
import pty_driver
import re

# cr50 firmware versions verified compatible with servod
VALID_VERSIONS = ['0.1.0/cr50_v1.9308_B.293-ad55183']


class cr50Error(Exception):
  """Exception class for Cr50."""


def restricted_command(func):
  """Decorator for methods which use restricted console command."""

  @functools.wraps(func)
  def wrapper(instance, *args, **kwargs):
    try:
      return func(instance, *args, **kwargs)
    except pty_driver.ptyError, e:
      if str(e) == 'Timeout waiting for response.':
        if instance._Get_ccd_level() == 'Locked':
          raise cr50Error('CCD console is locked. Perform the unlock process!')
      # Raise the original exception
      raise

  return wrapper


class cr50(pty_driver.ptyDriver):
  """Object to access drv=cr50 controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read kbd_en would be dispatched to
  call _Get_kbd_en.
  """

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
        control
      params: dictionary of params needed to perform operations on
        devices. The only params used now is 'subtype', which is used
        by get/set method of base class to decide how to dispatch
        request.
    """
    super(cr50, self).__init__(interface, params)
    self._logger.debug('')
    self._interface = interface
    if not hasattr(self._interface, '_ec_uart_bitbang_props'):
      self._interface._ec_uart_bitbang_props = {
          'enabled': False,
          'parity': None,
          'baudrate': None
      }

  def _issue_cmd_get_results(self, cmds, regex_list,
                             timeout=pty_driver.DEFAULT_UART_TIMEOUT):
    """Send \n to cr50 to make sure it is awake before sending cmds"""
    super(cr50, self)._issue_cmd_get_results('\n', [])
    return super(cr50, self)._issue_cmd_get_results(cmds, regex_list, timeout)

  def _Get_cold_reset(self):
    """Getter of cold_reset (active low).

    Returns:
      0: cold_reset on.
      1: cold_reset off.
    """
    result = self._issue_cmd_get_results(
        'ecrst', ['EC_RST_L is (asserted|deasserted)'])[0]
    if result is None:
      raise cr50Error('Cannot retrieve ecrst result on cr50 console.')
    return 0 if result[1] == 'asserted' else 1

  def _Set_cold_reset(self, value):
    """Setter of cold_reset (active low).

    Args:
      value: 0=on, 1=off.
    """
    if value == 0:
      self._issue_cmd('ecrst on')
    else:
      self._issue_cmd('ecrst off')

  def _Get_ccd_state(self):
    """Run a basic command that should take a short amount of time to check
    if ccd endpoints are still working.
    Returns:
      0: ccd is off.
      1: ccd is on.
    """
    try:
      # If gettime fails then the cr50 console is not working, which means
      # ccd is not working
      result = self._issue_cmd_get_results('gettime', ['.'], 3)
    except:
      return 0
    return 1

  def _Get_warm_reset(self):
    """Getter of warm_reset (active low).

    Returns:
      0: warm_reset on.
      1: warm_reset off.
    """
    result = self._issue_cmd_get_results(
        'sysrst', ['SYS_RST_L is (asserted|deasserted)'])[0]
    if result is None:
      raise cr50Error('Cannot retrieve sysrst result on cr50 console.')
    return 0 if result[1] == 'asserted' else 1

  def _Set_warm_reset(self, value):
    """Setter of warm_reset (active low).

    Args:
      value: 0=on, 1=off.
    """
    if value == 0:
      self._issue_cmd('sysrst on')
    else:
      self._issue_cmd('sysrst off')

  @restricted_command
  def _Get_pwr_button(self):
    """Getter of pwr_button.

    Returns:
      0: power button press.
      1: power button release.
    """
    result = self._issue_cmd_get_results(
        'powerbtn', ['powerbtn: (forced press|pressed|released)'])[0]
    if result is None:
      raise cr50Error('Cannot retrieve power button result on cr50 console.')
    return 1 if result[1] == 'released' else 0


  def _Set_pwr_button(self, value):
    """CCD doesn't support pwr_button. Tell user about pwr_button_hold"""
    raise cr50Error('pwr_button not supported use pwr_button_hold')


  def _Get_reset_count(self):
    """Getter of reset count.

    Returns:
        The reset count
    """
    result = self._issue_cmd_get_results('sysinfo', ['Reset count: (\d+)'])[0]
    if result is None:
      raise cr50Error('Cannot retrieve the reset count on cr50 console.')
    return result[1]

  def _Get_devid(self):
    """Getter of devid.

    Returns:
        The cr50 devid string
    """
    result = self._issue_cmd_get_results(
        'sysinfo', ['DEV_ID:\s+(0x[0-9a-z]{8} 0x[0-9a-z]{8})'])[0][1]
    if result is None:
      raise cr50Error('Cannot retrieve the devid result on cr50 console.')
    return result

  def _Get_ver(self):
    """Getter of ver.

    Returns:
        The cr50 version string
    """
    result = self._issue_cmd_get_results('ver', ['RW_(A|B):\s+\*\s+(\S+)\s'])[0]
    if result is None:
      raise cr50Error('Cannot retrieve the version result on cr50 console.')
    return result[2]

  def _Get_ver_valid(self):
    """Getter of ver_valid.

    Returns:
        Boolean: Is the cr50 version string one of the validated versions?
    """
    ver = self._Get_ver()
    valid = ver in VALID_VERSIONS
    if not valid:
      logging.warn('Detected cr50 version: %s', ver)
      logging.warn('Not in valid versions: %s', VALID_VERSIONS)
    return valid

  def _Set_cr50_reboot(self, value):
    """Reboot cr50 ignoring the value."""
    self._issue_cmd('reboot')

  def _Get_ccd_level(self):
    """Getter of ccd_level.

    Returns:
      lock, unlock, or open based on the current ccd privilege level.
    """
    result = self._issue_cmd_get_results('ccd',
                                         ['State:\s+(Lock|Unlock|Open)'])[0]
    if result is None:
      raise cr50Error('Cannot retrieve ccd privilege level on cr50 console.')
    return result[1].lower()

  def _Set_ccd_noop(self, value):
    """Used to ignore servo controls"""
    pass

  def _Get_ccd_noop(self):
    """Used to ignore servo controls"""
    return 'ERR'

  def _get_ccd_cap_state(self, cap):
    """Get the current state of the ccd capability"""
    result = self._issue_cmd_get_results('ccdstate', ['%s:([^\n]*)\n' % cap])
    return result[0][1].strip()

  def _Get_ccd_testlab(self):
    """Getter of ccd_testlab.

    Returns:
      'on' or 'off' if ccd testlab mode is enabled or disabled. 'unsupported'
      if cr50 doesn't have testlab support.
    """
    result = self._issue_cmd_get_results(
        'ccd testlab', ['(CCD test lab mode (ena|dis)|Access Denied)'])[0][1]
    if result == 'Access Denied':
      return 'unsupported'
    return 'on' if 'ena' in result else 'off'

  def _Set_ccd_testlab(self, value):
    """Setter of ccd_testlab.

    We dont want to accidentally disable ccd testlab mode. Only accept the value
    open. This will change the ccd privilege level without any physical
    presence.

    Args:
      value: 'open'
    """
    if value == 'open':
      self._issue_cmd('ccd testlab open')
    else:
      raise ValueError("Invalid ccd testlab setting: '%s'. Try 'open'" % value)

  def _Get_ccd_keepalive_en(self):
    """Getter of ccd_keepalive_en.

    Returns:
      0: keepalive disabled.
      1: keepalive enabled.
    """
    rdd = self._get_ccd_cap_state('Rdd')
    return 'on' if 'keepalive' in rdd else 'off'

  def _Set_ccd_keepalive_en(self, value):
    """Setter of ccd_keepalive_en.

    Args:
      value: 0=off, 1=on.
    """
    if value == 'off' or value == 'on':
      self._issue_cmd('rddkeepalive %s' % value)
    else:
      raise ValueError("Invalid ec_keepalive_en setting: '%s'. Try one of "
                       "'on', or 'off'." % value)

  def _Get_ec_uart_bitbang_en(self):
    return self._interface._ec_uart_bitbang_props['enabled']

  def _Set_ec_uart_bitbang_en(self, value):
    if value:
      # We need parity and baudrate settings in order to enable bit banging.
      if not self._interface._ec_uart_bitbang_props['parity']:
        raise ValueError("No parity set.  Try setting 'ec_uart_parity' first.")

      if not self._interface._ec_uart_bitbang_props['baudrate']:
        raise ValueError(
            "No baud rate set.  Try setting 'ec_uart_baudrate' first.")

      # The EC UART index is 2.
      cmd = '%s %s %s' % ('bitbang 2',
                          self._interface._ec_uart_bitbang_props['baudrate'],
                          self._interface._ec_uart_bitbang_props['parity'])
      try:
        result = self._issue_cmd_get_results(cmd, ['Bit bang enabled'])
        if result is None:
          raise cr50Error('Unable to enable bit bang mode!')
      except pty_driver.ptyError:
        raise cr50Error('Unable to enable bit bang mode!')

      self._interface._ec_uart_bitbang_props['enabled'] = 1

    else:
      self._issue_cmd('bitbang 2 disable')
      self._interface._ec_uart_bitbang_props['enabled'] = 0

  def _Get_ccd_ec_uart_parity(self):
    self._logger.debug('%r', self._interface._ec_uart_bitbang_props)
    return self._interface._ec_uart_bitbang_props['parity']

  def _Set_ccd_ec_uart_parity(self, value):
    if value.lower() not in ['odd', 'even', 'none']:
      raise ValueError("Bad parity (%s). Try 'odd', 'even', or 'none'." % value)

    self._interface._ec_uart_bitbang_props['parity'] = value
    self._logger.debug('%r', self._interface._ec_uart_bitbang_props)

  def _Get_ccd_ec_uart_baudrate(self):
    return self._interface._ec_uart_bitbang_props['baudrate']

  def _Set_ccd_ec_uart_baudrate(self, value):
    if value is not None and value.lower() not in [
        'none', '1200', '2400', '4800', '9600', '19200', '38400', '57600',
        '115200'
    ]:
      raise ValueError("Bad baud rate(%s). Try '1200', '2400', '4800', '9600',"
                       " '19200', '38400', '57600', or '115200'" % value)

    if value.lower() == 'none':
      value = None
    self._interface._ec_uart_bitbang_props['baudrate'] = value

  def _Get_ec_boot_mode(self):
    boot_mode = 'off'
    result = self._issue_cmd_get_results('gpioget EC_FLASH_SELECT',
                                         ['\s+([01])\s+EC_FLASH_SELECT'])[0]
    if result:
      if result[0] == '1':
        boot_mode = 'on'

    return boot_mode

  def _Set_ec_boot_mode(self, value):
    self._issue_cmd('gpioset EC_FLASH_SELECT %s' % value)

  def _Get_uut_boot_mode(self):
    result = self._issue_cmd_get_results('gpiocfg', ['gpiocfg(.*)>'])[0][0]
    if re.search('GPIO0_GPIO15:\s+read 0 drive 0', result):
        return 'on'
    return 'off'

  def _Set_uut_boot_mode(self, value):
    self._issue_cmd('gpioset EC_TX_CR50_RX_OUT %s' % value)
