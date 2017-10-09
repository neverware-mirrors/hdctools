# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
    Login driver to handle the login hurdle on the CPU uart console.
    This driver exposes methods to login, logout, set password, and
    username to login, and check if a session is logged in.
"""
import logging
import time

import pty_driver


class loginError(Exception):
  """Exception class for login errors."""

class login(pty_driver.ptyDriver):
  """ Wrapper class around ptyDriver to handle communication
      with the AP console.
  """

  # This is a class level variable because each
  # servo command runs on their own instance of
  # dutMetadata. We share it across instances
  # to allow for updating and retrieval.

  # TODO(coconutruben): right now the defaults are hard coded
  # into the driver. Evaluate if it makes more sense for the
  # defaults to be set by the xml commands.
  _login_info = {
      'username'  : 'root',
      'password'  : 'test0000'
  }

  def __init__(self, interface, params):
    """Initializes the login driver.

    Args:
      interface: A driver interface object. This is the AP uart interface.
      params: A dictionary of parameters, but is ignored.
    """
    super(login, self).__init__(interface, params)
    self._logger.debug("")

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
    # TODO(coconutruben): currently, this assumes localhost as the
    # host name, and a specific pattern for PS1. Make this more
    # robust to OS changes by generating the regex based on the
    # PS1 variable.
    try:
      self._issue_cmd_get_results([''], ['localhost.*\s+[#$]'])
      return 1
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
    # TODO(coconutruben): the login sequence relies on timing currently.
    # Consider if it would be more robust to use fdexpect code directly
    # to see when to send the username, and the password.
    if value == 1:
      # 1 means login desired.
      if not self._Get_login():
        with self._open():
          self._send([self._login_info['username'],
                      self._login_info['password']],
                     0.1, False)
      time.sleep(0.1)
    if value == 0:
      # 0 means logout desired.
      if self._Get_login():
        self._issue_cmd(['exit'])
