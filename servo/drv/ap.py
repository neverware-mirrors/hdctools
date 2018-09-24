# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
    AP console communications driver. Automations that need to interact
    with the AP console should inherit from this driver, or build a composition
    containing this driver.
    This driver exposes methods to login, logout, set password, and
    username to login, and check if a session is logged in.
"""
import logging
import pexpect
import time

import pty_driver


class apError(pty_driver.ptyError):
  """Exception class for AP errors."""


class ap(pty_driver.ptyDriver):
  """ Wrapper class around ptyDriver to handle communication
      with the AP console.
  """

  # This is a class level variable because each
  # servo command runs on their own instance of
  # dutMetadata. We share it across instances
  # to allow for updating and retrieval.

  # TODO(coconutruben): right now the defaults are hard coded
  # into the driver. Evaluate if it makes more sense for the
  # defaults to be set by the xml commands, or to allow servo
  # invocation to overwrite them.
  _login_info = {'username': 'root', 'password': 'test0000'}

  def __init__(self, interface, params):
    """Initializes the AP driver.

    Args:
      interface: A driver interface object. This is the AP uart interface.
      params: A dictionary of parameters, but is ignored.
    """
    super(ap, self).__init__(interface, params)
    self._logger.debug('')

  def _Get_password(self):
    """ Returns password currently used for login attempts. """
    return self._login_info['password']

  def _Set_password(self, value):
    """ Set |value| as password for login attempts. """
    self._login_info['password'] = value

  def _Get_username(self):
    """ Returns username currently used for login attempts. """
    return self._login_info['username']

  def _Set_username(self, value):
    """ Set |value| as username for login attempts. """
    self._login_info['username'] = value

  def _Get_login(self):
    """ Heuristic to determine if a session is logged in
        on the CPU uart terminal.

        Sends a newline to the terminal, and evaluates the output
        to determine login status.

        Returns:
          True 1 a session is logged in, 0 otherwise.
    """
    try:
      match = self._issue_cmd_get_results(
          [''],
          [r'localhost\x1b\[01;34m\s'
           r'[^\s/]+\s[#$]|'
           r'localhost login:'])
      return 0 if 'localhost login:' in match[0] else 1
    except pty_driver.ptyError:
      return 0

  def _Set_login(self, value):
    """ Login/out of a session on the CPU uart terminal.

        Uses username and password stored in |_login_info| to
        attempt login.
    """
    # TODO(coconutruben): the login/logout logic fails silently and user has
    # to call login command again to verify. Consider if raising an error on
    # failure here is appropiate.
    if value == 1:
      # 1 means login desired.
      if not self._Get_login():
        with self._open():
          # Make sure uart capture does not interfere with matching the expected
          # response
          self._interface.pause_capture()
          try:
            self._send('')
            self._child.expect('localhost login:', 3)
            match = self._child.match
            if not match:
              raise apError('Username prompt did not show up on login attempt')
            self._send(self._login_info['username'], flush=False)
            self._child.expect('Password:', 2)
            match = self._child.match
            if not match:
              raise apError('Password prompt did not show up on login attempt')
            self._send(self._login_info['password'], flush=False)
          except pexpect.TIMEOUT:
            raise apError('Timeout waiting for response when attempting to '
                          'log into AP console.')
          finally:
            # Reenable capturing the console output
            self._interface.resume_capture()
        time.sleep(0.1)
    if value == 0:
      # 0 means logout desired.
      if self._Get_login():
        self._issue_cmd(['exit'])
