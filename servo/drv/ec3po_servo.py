# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servo generic controls through ec3po.
"""

import logging
import time

import pty_driver
import servo

# EC console mask for enabling only command channel
COMMAND_CHANNEL_MASK = 0x1


class ec3poServoError(Exception):
  """Exception class."""


class ec3poServo(pty_driver.ptyDriver):
  """Parent object to servo console controls."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: ec3po interface object to handle low-level communication to
        control
      params: dictionary of params needed
    Raises:
      ec3poServoError: on init failure
    """
    super(ec3poServo, self).__init__(interface, params)

    if 'console' in params:
      if params['console'] == 'enhanced' and \
          type(interface) is servo.ec3po_interface.EC3PO:
        interface._console.oobm_queue.put('interrogate never enhanced')
      else:
        raise ec3poServoError('Enhanced console must be ec3po!')

    self._logger.debug('')

  def _limit_channel(self):
    """Suppress background output on the EC console.

    This limits the output to the command channel, which will only print
    output from commands issued from servod, and suppresses synchronous
    EC output from higher priority tasks that might corrupt the command's
    output. The old setting is saved for restoring later.
    """
    self._issue_cmd('chan save')
    self._issue_cmd('chan %d' % COMMAND_CHANNEL_MASK)

  def _restore_channel(self):
    """Load saved channel setting."""
    self._issue_cmd('chan restore')

  def _issue_safe_cmd_get_results(self, cmd, rx):
    """Run a command and regex the response, safely.

    This disables EC debug output while waiting for a
    command response, to prevent unexpected output interleaved
    with expected data.

    Args:
      (See pty_driver._issue_cmd_get_results)
      cmd: command string to run.
      rx: List of regex strings to match in response.

    Returns:
      List of match lists, containing matched string plus extracted values.
    """
    res = None
    self._limit_channel()
    try:
      res = self._issue_cmd_get_results(cmd, rx)
    finally:
      self._restore_channel()
    return res
