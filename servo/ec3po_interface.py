# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo interface for the EC-3PO console interpreter."""

from __future__ import print_function

# pylint: disable=cros-logging-import
import ctypes
import logging
import multiprocessing
import os
import pty
import stat
import termios
import tty

import ec3po
import uart


class EC3PO(uart.Uart):
  """Class for an EC-3PO console interpreter instance.

  This includes both the interpreter and the console objects for one UART.
  """

  def __init__(self, raw_ec_uart, source_name):
    """Provides the interface to the EC-3PO console interpreter.

    Args:
      raw_ec_uart: A string representing the actual PTY of the EC UART.
      source_name: A user friendly name documenting the source of this PTY.
    """
    # Run Fuart init.
    super(EC3PO, self).__init__()
    self._logger = logging.getLogger('EC3PO Interface')
    # Create the console and interpreter passing in the raw EC UART PTY.
    self._raw_ec_uart = raw_ec_uart
    self._source = source_name

    # Create some pipes to communicate between the interpreter and the console.
    # The command pipe is bidirectional.
    cmd_pipe_interactive, cmd_pipe_interp = multiprocessing.Pipe()
    # The debug pipe is unidirectional from interpreter to console only.
    dbg_pipe_interactive, dbg_pipe_interp = multiprocessing.Pipe(duplex=False)

    # Create an interpreter instance.
    itpr = ec3po.interpreter.Interpreter(raw_ec_uart, cmd_pipe_interp,
                                         dbg_pipe_interp, logging.INFO)
    self._itpr = itpr
    itpr._logger = logging.getLogger('Interpreter')

    # Spawn an interpreter process.
    itpr_process = multiprocessing.Process(target=ec3po.interpreter.StartLoop,
                                           args=(itpr,))
    # Make sure to kill the interpreter when we terminate.
    itpr_process.daemon = True
    # Start the interpreter.
    itpr_process.start()
    self.itpr_process = itpr_process
    # The interpreter starts up in the connected state.
    self._interp_connected = 'on'

    # Open a new pseudo-terminal pair.
    (master_pty, user_pty) = pty.openpty()
    (interface_pty, control_pty) = pty.openpty()

    tty.setraw(master_pty, termios.TCSADRAIN)
    tty.setraw(interface_pty, termios.TCSADRAIN)

    # Set the permissions to 660.
    os.chmod(
        os.ttyname(user_pty),
        (stat.S_IRGRP | stat.S_IWGRP | stat.S_IRUSR | stat.S_IWUSR))
    os.chmod(
        os.ttyname(control_pty),
        (stat.S_IRGRP | stat.S_IWGRP | stat.S_IRUSR | stat.S_IWUSR))

    # Change the owner and group of the PTY to the user who started servod.
    try:
      uid = int(os.environ.get('SUDO_UID', -1))
    except TypeError:
      uid = -1

    try:
      gid = int(os.environ.get('SUDO_GID', -1))
    except TypeError:
      gid = -1
    os.fchown(user_pty, uid, gid)
    os.fchown(control_pty, uid, gid)

    # Create a console.
    c = ec3po.console.Console(master_pty, os.ttyname(user_pty), interface_pty,
                              cmd_pipe_interactive, dbg_pipe_interactive)
    self._console = c
    c._logger = logging.getLogger('Console')
    # Spawn a console process.
    v = multiprocessing.Value(ctypes.c_bool, False)
    self._command_active = v
    console_process = multiprocessing.Process(target=ec3po.console.StartLoop,
                                              args=(c, v))
    # Make sure to kill the console when we terminate.
    console_process.daemon = True
    # Start the console.
    console_process.start()
    self._logger.debug('Console: %s', self._console)

    self._logger.debug('User console: %s', os.ttyname(user_pty))
    self._logger.debug('Control console: %s', os.ttyname(control_pty))
    self._pty = os.ttyname(user_pty)
    self._control_pty = os.ttyname(control_pty)
    self._cmd_pipe_int = cmd_pipe_interactive

    self._logger.info('-------------------- %s console on: %s', self._source,
                      os.ttyname(user_pty))

  def get_pty(self):
    """Gets the path of the served PTY."""
    self._logger.debug('get_pty: %s', self._pty)
    return self._pty

  def get_control_pty(self):
    """Gets the path of the served control PTY."""
    self._logger.debug('get_pty: %s', self._control_pty)
    return self._control_pty

  def get_command_lock(self):
    self._command_active.value = True
    self._logger.debug('acquire lock for %s: %s', self._control_pty,
                       self._command_active.value)

  def release_command_lock(self):
    self._command_active.value = False
    self._logger.debug('release lock for %s: %s', self._control_pty,
                       self._command_active.value)

  def set_interp_connect(self, state):
    """Set the interpreter's connection state to the UART.

    Args:
      state: An integer (0 or 1) indicating whether to connect to the UART or
        not.
    """
    self._logger.debug('EC3PO Interpreter connection request: \'%r\'', state)
    if state == 1:
      self._cmd_pipe_int.send('reconnect')
      self._interp_connected = 'on'
    else:
      self._cmd_pipe_int.send('disconnect')
      self._interp_connected = 'off'
    return

  def get_interp_connect(self):
    """Get the state of the interpreter connection to the UART."""
    return self._interp_connected
