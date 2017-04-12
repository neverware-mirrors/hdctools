# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of drv=cr50.

Provides the following Cr50 controlled function:
  cold_reset
  warm_reset
  ccd_ec_uart_en
"""

import functools
import pty_driver


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
        if instance._Get_ccd_lock():
          raise cr50Error("CCD console is locked. Perform the unlock process!")
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
    self._logger.debug("")
    self._ec_uart_en = None

  def _issue_cmd_get_results(self, cmds, regex_list,
                             timeout=pty_driver.DEFAULT_UART_TIMEOUT):
    """Send \n to cr50 to make sure it is awake before sending cmds"""
    super(cr50, self)._issue_cmd_get_results('\n', [])
    return super(cr50, self)._issue_cmd_get_results(cmds, regex_list, timeout)

  def _Get_cold_reset(self):
    """Getter of cold_reset.

    Returns:
      0: cold_reset off.
      1: cold_reset on.
    """
    result = self._issue_cmd_get_results(
        "ecrst", ["EC_RST_L is (asserted|deasserted)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve ecrst result on cr50 console.")
    return 1 if result[1] == "asserted" else 0

  def _Set_cold_reset(self, value):
    """Setter of cold_reset.

    Args:
      value: 0=off, 1=on.
    """
    if value == 0:
      self._issue_cmd("ecrst off")
    else:
      self._issue_cmd("ecrst on")

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
        result = self._issue_cmd_get_results("gettime", ['.'], 3)
    except:
        return 0
    return 1

  def _Get_warm_reset(self):
    """Getter of warm_reset.

    Returns:
      0: warm_reset off.
      1: warm_reset on.
    """
    result = self._issue_cmd_get_results(
        "sysrst", ["SYS_RST_L is (asserted|deasserted)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve sysrst result on cr50 console.")
    return 1 if result[1] == "asserted" else 0

  def _Set_warm_reset(self, value):
    """Setter of warm_reset.

    Args:
      value: 0=off, 1=on.
    """
    if value == 0:
      self._issue_cmd("sysrst off")
    else:
      self._issue_cmd("sysrst on")

  @restricted_command
  def _Get_pwr_button(self):
    """Getter of pwr_button.

    Returns:
      0: power button press.
      1: power button release.
    """
    result = self._issue_cmd_get_results(
        "powerbtn", ["powerbtn: (forced press|pressed|released)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve power button result on cr50 console.")
    return 1 if result[1] == "released" else 0

  def _Get_reset_count(self):
    """Getter of ccd_lock.

    Returns:
        The reset count
    """
    result = self._issue_cmd_get_results(
        "sysinfo", ["Reset count: (\d+)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve the reset count on cr50 console.")
    return result[1]

  def _Get_ver(self):
    """Getter of ver.

    Returns:
        The cr50 version string
    """
    result = self._issue_cmd_get_results(
        "ver", ["RW_(A|B):\s+\*\s+(.+)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve the version result on cr50 console.")
    return result[2]

  def _Set_cr50_reboot(self, value):
    """Reboot cr50 ignoring the value."""
    self._issue_cmd("reboot")

  def _Get_ccd_lock(self):
    """Getter of ccd_lock.

    Returns:
      0: CCD restricted console lock disabled.
      1: CCD restricted console lock enabled.
    """
    result = self._issue_cmd_get_results(
        "lock", ["The restricted console lock is (enabled|disabled)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve ccd lock result on cr50 console.")
    return 1 if result[1] == "enabled" else 0

  def _Set_ccd_noop(self, value):
    """Used to ignore servo controls"""
    pass

  def _Get_ccd_noop(self):
    """Used to ignore servo controls"""
    return "ERR"

  @restricted_command
  def _Get_ccd_ec_uart_en(self):
    """Getter of ccd_ec_uart_en.

    Returns:
      0: EC UART disabled.
      1: EC UART enabled.
    """
    # Check the EC UART result as the AP's and Cr50's UART are always on.
    result = self._issue_cmd_get_results(
        "ccd", ["EC UART:\s*(enabled|disabled)"])[0]
    if result is None:
      raise cr50Error("Cannot retrieve ccd uart result on cr50 console.")
    return "on" if result[1] == "enabled" else "off"

  def _Set_ccd_ec_uart_en(self, value):
    """Setter of ccd_ec_uart_en.

    Args:
      value: 0=off, 1=on.
    """
    if value == "off" or value == "on":
      self._issue_cmd("ccd uart %s" % value)
      self._ec_uart_en = value
    elif value == "restore":
      if self._ec_uart_en:
        self._issue_cmd("ccd uart %s" % self._ec_uart_en)
    else:
      raise ValueError("Invalid ec_uart_en setting: '%s'. Try one of "
                       "'on', 'off', or 'restore'." % value)
