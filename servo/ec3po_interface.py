# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo interface for the EC-3PO console interpreter."""

from __future__ import print_function

# pylint: disable=cros-logging-import
import ctypes
import errno
import functools
import logging
import os
import pty
import stat
import sys
import termios
import time
import tty

from ec3po import console
from ec3po import interpreter
from ec3po import threadproc_shim

import uart


def _RunCallbacks(*callbacks):
  """Run the provided callbacks.  Return the value from the last one."""
  retval = None
  for callback in callbacks:
    retval = callback()
  return retval


def _OsPipeFiles():
  """Like os.pipe(), except returns file objects instead of file descriptors.

  Returns: (read_file, write_file) - A two-item tuple of the read and write
      sides of the pipe.
  """
  rd_fd, wr_fd = os.pipe()
  try:
    return os.fdopen(rd_fd, 'r'), os.fdopen(wr_fd, 'w')
  # If anything went wrong with fdopen(), do our best to clean up.
  except:
    # Save original exception for re-raising, in case os.close() triggers an
    # exception.  Note that saving exc_traceback here creates a circular
    # reference.
    exc_type, exc_value, exc_traceback = sys.exc_info()
    try:
      try:
        os.close(rd_fd)
      except:
        pass
      try:
        os.close(wr_fd)
      except:
        pass
      # Re-raise the original exception.
      raise exc_type, exc_value, exc_traceback
    finally:
      # Break the exc_traceback circular reference.
      del exc_type, exc_value, exc_traceback


def _SendShutdown(pipe_wr):
  """Indicate shutdown by unblocking reads on a pipe.

  Args:
    pipe_wr: file object wrapping write side of a pipe; must support .fileno()
        and .close()

  EPIPE from os.write() to the fd will be suppressed.  Any other exceptions will
  be allowed to propagate.  pipe_wr.close() will always be attempted, even if
  os.write() to the fd raised an exception.
  """
  try:
    os.write(pipe_wr.fileno(), '.')
  except (OSError, IOError) as error:
    if error.errno != errno.EPIPE:
      raise
  finally:
    pipe_wr.close()


class EC3PO(uart.Uart):
  """Class for an EC-3PO console interpreter instance.

  This includes both the interpreter and the console objects for one UART.
  """

  def __init__(self, raw_ec_uart, source_name, device):
    """Provides the interface to the EC-3PO console interpreter.

    Args:
      raw_ec_uart: A string representing the actual PTY of the EC UART.
      source_name: A user friendly name documenting the source of this PTY.
      device: A tuple of the USB device info (vid, pid, serialname)
    """
    # Run Fuart init.
    uart.Uart.__init__(self)
    self._logger = logging.getLogger('%s - EC3PO Interface' % source_name)
    # Create the console and interpreter passing in the raw EC UART PTY.
    self._raw_ec_uart = raw_ec_uart
    self._source = source_name
    self._device = device

    # Create some pipes to communicate between the interpreter and the console.
    # The command pipe is bidirectional.
    cmd_pipe_interactive, cmd_pipe_interp = threadproc_shim.Pipe()
    # The debug pipe is unidirectional from interpreter to console only.
    dbg_pipe_interactive, dbg_pipe_interp = threadproc_shim.Pipe(duplex=False)

    # Use a separate shutdown notification pipe for each subprocess or thread
    # because there is no guarantee that multiple select()/poll()/epoll()
    # pollers would be woken upon blocked->unblocked transition.
    #
    # So long as subprocesses are in use, it is important that the subprocesses
    # close their write-side pipe files when they start, otherwise the closing
    # of them from the main process will have no effect.
    #
    # It is also desirable for a subprocess to close the read-side pipe file of
    # any pipe which it is not using, e.g. console subprocess should close the
    # read-side of the interpreter shutdown pipe, in addition to closing its
    # write side.  This is not truly necessary for correctness, but avoids
    # unnecessarily holding open a file descriptor in a process that should
    # never use it.
    #
    # This will become simpler after ec3po is updated to use threads instead of
    # subprocesses, which is being done as part of http://crbug.com/79684405.
    self._itpr_shutdown_pipe_rd, self._itpr_shutdown_pipe_wr = _OsPipeFiles()
    self._c_shutdown_pipe_rd, self._c_shutdown_pipe_wr = _OsPipeFiles()

    # Create an interpreter instance.
    itpr = interpreter.Interpreter(raw_ec_uart, cmd_pipe_interp,
                                   dbg_pipe_interp, logging.INFO, self._source)
    self._itpr = itpr
    itpr._logger = logging.getLogger('Interpreter')

    # Spawn an interpreter process.
    itpr_process = threadproc_shim.ThreadOrProcess(
        target=_RunCallbacks,
        args=(
            threadproc_shim.DoIf(subprocs=self._itpr_shutdown_pipe_wr.close),
            threadproc_shim.DoIf(subprocs=self._c_shutdown_pipe_rd.close),
            threadproc_shim.DoIf(subprocs=self._c_shutdown_pipe_wr.close),
            functools.partial(
                interpreter.StartLoop, itpr,
                shutdown_pipe=self._itpr_shutdown_pipe_rd)))
    # Make sure to kill the interpreter when we terminate.
    itpr_process.daemon = True
    # Start the interpreter.
    itpr_process.start()
    self.itpr_process = itpr_process
    # The interpreter starts up in the connected state.
    self._interp_connected = 'on'

    # The original console loglevel will match the logger level.
    self._console_loglevel = self._logger.getEffectiveLevel()

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

    # Close pts to indicate HUP to ec3po.
    user_pty_name = os.ttyname(user_pty)
    os.close(user_pty)

    # Create a console.
    c = console.Console(master_pty, user_pty_name, interface_pty,
                        cmd_pipe_interactive, dbg_pipe_interactive,
                        self._source)
    self._console = c
    c._logger = logging.getLogger('Console')
    # Spawn a console process.
    v = threadproc_shim.Value(ctypes.c_bool, False)
    self._command_active = v
    console_process = threadproc_shim.ThreadOrProcess(
        target=_RunCallbacks,
        args=(
            threadproc_shim.DoIf(subprocs=self._itpr_shutdown_pipe_rd.close),
            threadproc_shim.DoIf(subprocs=self._itpr_shutdown_pipe_wr.close),
            threadproc_shim.DoIf(subprocs=self._c_shutdown_pipe_wr.close),
            functools.partial(
                console.StartLoop, c, v,
                shutdown_pipe=self._c_shutdown_pipe_rd)))
    # Make sure to kill the console when we terminate.
    console_process.daemon = True
    # Start the console.
    console_process.start()

    self.console_process = console_process

    self._logger.debug('Console: %s', self._console)

    self._logger.debug('User console: %s', user_pty_name)
    self._logger.debug('Control console: %s', os.ttyname(control_pty))
    self._pty = user_pty_name
    self._control_pty = os.ttyname(control_pty)
    self._cmd_pipe_int = cmd_pipe_interactive

    self._logger.info('-------------------- %s console on: %s', self._source,
                      user_pty_name)

  def get_device_info(self):
    """Get the usb device information."""
    return self._device

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

  def set_loglevel(self, value):
    """'Setter' of the console loglevel.

    Args:
      level: a logging level string 'debug', 'info', 'warning', 'error',
             'critical'
    """
    level = logging.getLevelName(value.upper())
    if not isinstance(level, int):
        raise Exception('invalid loglevel %r' % value)
    self._console_loglevel = level
    self._console.oobm_queue.put('loglevel %d' % level)

  def get_loglevel(self):
    """Returns the current loglevel."""
    return logging.getLevelName(self._console_loglevel).lower()

  def set_timestamp(self, state):
    """Enable timestamps.

    Args:
      1 to enable 0 to disable timestamps on the console
    """
    mode = 'on' if state else 'off'
    self._logger.debug('EC3PO turn %s timestamp', mode)
    self._console.oobm_queue.put('timestamp ' + mode)

  def get_timestamp(self):
    """Returns the current timestamp setting."""
    return 'on' if self._console.timestamp_enabled else 'off'

  def close(self):
    """Turn down the ec3po interface by terminating interpreter & console."""
    # Notify subprocesses/threads of desire to shutdown.
    #
    # The write()s are necessary in addition to close() for the signal-activated
    # shutdown cases.  Without the write()s, not all of the subprocesses do not
    # get notified immediately, and the subprocess join timeout below is reached
    # for some of them.  (No tracebacks or deadlocks though, all of servod still
    # exits cleanly-ish after the join timeouts.)
    #
    # The author of this comment is unsure why the write()s are needed, and is
    # uninterested in troubleshooting further since having the write()s appears
    # to work without downsides, and the author of this comment is in the
    # process of migrating ec3po from using subprocesses to using threads.  The
    # use of shutdown notification pipes will remain with threads (it was added
    # specifically for that migration), and the need for these write()s will be
    # revisited then.
    #
    # TODO(b/79684405): When switching ec3po from subprocesses to threads, test
    # whether these writes are still needed.  If so, consider troubleshooting
    # further at that time.
    try:
      _SendShutdown(self._itpr_shutdown_pipe_wr)
    finally:
      _SendShutdown(self._c_shutdown_pipe_wr)

    total_timeout = 2
    end_time = time.time() + total_timeout
    self.itpr_process.join(timeout=total_timeout)
    self.console_process.join(timeout=max(0, end_time - time.time()))

    self._logger.info('ec3po interpreter process is_alive=%s after %s timeout' %
                      (self.itpr_process.is_alive(), total_timeout))
    self._logger.info('ec3po console process is_alive=%s after %s timeout' %
                      (self.console_process.is_alive(), total_timeout))
    self._logger.info('Closing EC3PO console at %s' % self._pty)

    if threadproc_shim.USING_SUBPROCS:
      self._itpr_shutdown_pipe_rd.close()
      self._c_shutdown_pipe_rd.close()
