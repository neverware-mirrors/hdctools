# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This uses the i2c-pseudo driver to implement a local Linux I2C adapter of a
Servo/DUT I2C bus.
"""

import collections
import errno
import logging
import os
import select
import threading
import os

_CONTROLLER_DEVICE_PATH = b'/dev/i2c-pseudo-controller'
_CMD_END_CHAR = b'\n'
_HEADER_SEP_CHAR = b' '
_DATA_SEP_CHAR = b':'
# This is a printf()-style format string for the i2c-pseudo I2C_XFER_REPLY
# write command.
#
# The positional fields are, in order:
#   xfer_id: int or ctypes.c_ubyte or equivalent
#   msg_id: int or ctypes.c_ubyte or equivalent
#   addr: int or ctypes.c_ubyte or equivalent
#   flags: int or ctypes.c_ubyte or equivalent
#   errno: int or ctypes.c_ubyte or equivalent
#
# See Documentation/i2c/pseudo-controller-interface from Linux for more details.
_I2C_XFER_REPLY_FMT_STR = _HEADER_SEP_CHAR.join((
    b'I2C_XFER_REPLY', b'%d', b'%d', b'0x%04X', b'0x%04X', b'%d'))
_READ_SIZE = 1024
_I2C_ADAPTER_TIMEOUT_MS = 5000
_EPOLL_EVENTMASK_NO_WRITES = select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP
_EPOLL_EVENTMASK_WITH_WRITES = _EPOLL_EVENTMASK_NO_WRITES | select.EPOLLOUT

# This value is guaranteed per include/uapi/linux/i2c.h
I2C_M_RD = 0x0001
# This value is implicitly subject to change.
I2C_M_RECV_LEN = 0x0400


def default_controller_path():
  """Get the default i2c-pseudo controller device path.

  Returns:
    bytes - absolute path
  """
  path = _CONTROLLER_DEVICE_PATH
  assert os.path.isabs(path)
  return path


class I2cPseudoAdapter(object):
  """This class implements a Linux I2C adapter for the servo I2C bus.

  This class is a controller for the i2c-pseudo Linux kernel module.  See its
  documentation for background.

  Thread safety:
    This class is internally multi-threaded.
    It is safe to use the public interface from multiple threads concurrently.

  Usage:
    adap = I2cPseudoAdapter.make_with_default_path(servo_i2c_bus)
    i2c_id = adap.start()
    ...
    adap.shutdown()
  """

  @staticmethod
  def make_with_default_path(servo_i2c_bus):
    """Make an instance using the default i2c-pseudo controller device path.

    Args:
      servo_i2c_bus: implementation of i2c_base.BaseI2CBus

    Returns:
      I2cPseudoAdapter
    """
    return I2cPseudoAdapter(default_controller_path(), servo_i2c_bus)

  def __init__(self, controller_device_path, servo_i2c_bus):
    """Initializer.  Does NOT create the pseudo adapter.

    Args:
      controller_device_path: bytes or str - path to the i2c-pseudo controller
          device file
      servo_i2c_bus: implementation of i2c_base.BaseI2CBus
    """
    self._logger = logging.getLogger('i2c_pseudo')
    self._logger.info(
        'attempting to initialize (not start yet!) I2C pseudo adapter '
        'controller_device_path=%r servo_i2c_bus=%r' %
        (controller_device_path, servo_i2c_bus))

    self._servo_i2c_bus = servo_i2c_bus
    self._controller_device_path = controller_device_path

    self._device_fd = None
    self._i2c_pseudo_id = None
    self._i2c_adapter_num = None

    self._epoll = None
    self._device_eventmask_lock = threading.Lock()
    self._device_epoll_eventmask = _EPOLL_EVENTMASK_NO_WRITES

    self._io_thread = None

    self._xfer_reqs = []
    self._in_tx = False

    self._device_read_buffers = []
    self._device_read_post_newline_idx = 0

    self._device_write_lock = threading.Lock()
    # self._device_write_lock must be held while popping items, processing
    # items, or appending to the right side.  That lock does NOT need to be held
    # when appending items to the left side.
    self._device_write_queue = collections.deque()

    self._startstop_lock = threading.Lock()
    self._started = False

    self._logger.info(
        'finished initializing I2C pseudo adapter (not started yet!)')

  def start(self):
    """Create and start the i2c-pseudo adapter.

    This method may be invoked repeatedly, including overlapping invocations
    from multiple threads.  Redundant invocations are a no-op.  When any one
    invocation has returned successfully (no exceptions), the I2C pseudo adapter
    has been started.

    If an invocation fails with an exception, the state of the object is
    undefined, and it should be abandoned.

    This MUST NOT be called during or after shutdown().
    """
    self._logger.info('attempting to start I2C pseudo adapter')

    with self._startstop_lock:
      assert self._started is not None

      if self._started:
        self._logger.warn('I2C pseudo adapter already started')
        return

      self._started = True
      self._device_fd = os.open(self._controller_device_path,
                                os.O_RDWR | os.O_NONBLOCK)
      self._epoll = select.epoll(sizehint=2)
      self._epoll.register(self._device_fd, self._device_epoll_eventmask)

      self._io_thread = threading.Thread(
          name='I2C-Pseudo-PyID-0x%X' % (id(self),),
          target=self._io_thread_run)
      self._io_thread.daemon = True
      self._io_thread.start()

      self._enqueue_simple_ctrlr_cmd((b'GET_PSEUDO_ID',))
      self._enqueue_simple_ctrlr_cmd((
          b'SET_ADAPTER_NAME_SUFFIX', b'(servod pid %d)' % (os.getpid(),)))
      self._enqueue_simple_ctrlr_cmd((
          b'SET_ADAPTER_TIMEOUT_MS', b'%d' % (_I2C_ADAPTER_TIMEOUT_MS,)))
      self._enqueue_simple_ctrlr_cmd((b'ADAPTER_START',))
      self._enqueue_simple_ctrlr_cmd((b'GET_ADAPTER_NUM',))
      self._do_device_writes()

      self._logger.info('finished starting I2C pseudo adapter')

  def servo_i2c_bus(self):
    """Get the i2c_base.BaseI2CBus implementation this object is using.

    Returns:
      i2c_base.BaseI2CBus
    """
    return self._servo_i2c_bus

  def controller_device_path(self):
    """Get the i2c-pseudo controller device file this object is using.

    Returns:
      bytes or str - path to the i2c-pseudo controller device file
    """
    return self._controller_device_path

  def i2c_pseudo_id(self):
    """Get the i2c-pseudo controller ID.

    Returns:
      None or int - The i2c-pseudo controller ID, or None if start() has not
        completed yet.
    """
    return self._i2c_pseudo_id

  def i2c_adapter_num(self):
    """Get the Linux I2C adapter number.

    Returns:
      None or int - The Linux I2C adapter number, or None if start() has not
          completed yet.
    """
    return self._i2c_adapter_num

  def is_running(self):
    """Check whether the pseudo controller is running.

    Returns:
      bool - True if the pseudo controller and its I/O thread are running, False
          otherwise, e.g. if the controller was either never started, or has
          been shutdown.
    """
    return self._io_thread is not None and self._io_thread.is_alive()

  def _reset_tx(self, in_tx):
    """Delete any queued I2C transfer requests and reset transaction state.

    Args:
      in_tx: bool - The internal transaction state is set to this value.
    """
    del self._xfer_reqs[:]
    self._in_tx = in_tx

  def _cmd_i2c_begin_xfer(self, line):
    """Allow queueing of I2C transfer requests.

    This always resets the internal transaction state to be in a transaction and
    have no I2C transfer requests queued.

    Args:
      line: str - The I2C_BEGIN_XFER line read from the i2c-pseudo device.
    """
    try:
      assert not self._in_tx
    finally:
      self._reset_tx(True)

  def _cmd_i2c_commit_xfer(self, line):
    """Perform the queued I2C transaction.

    This always resets the internal transaction state to not be in a transaction
    and have no I2C transfer requests queued.

    Args:
      line: str - The I2C_COMMIT_XFER line read from the i2c-pseudo device.
    """
    try:
      self._cmd_i2c_commit_xfer_internal(line)
    finally:
      self._reset_tx(False)

  def _cmd_i2c_commit_xfer_internal(self, line):
    """Perform the queued I2C transaction.

    Invocations to this should be wrapped in try:/finally: to always reset the
    internal transaction state, regardless of success or failure.

    Args:
      line: str - The I2C_COMMIT_XFER line read from the i2c-pseudo device.
    """
    assert self._in_tx
    if not self._xfer_reqs:
      return
    assert len(self._xfer_reqs) <= 2
    assert len(set(xfer_id for xfer_id, _, _, _, _, _ in self._xfer_reqs)) == 1
    assert len(set(addr for _, _, addr, _, _, _ in self._xfer_reqs)) == 1

    write_idx = None
    write_list = None
    read_idx = None
    read_count = None
    read_flags = 0
    retval = None
    errnum = 0

    for xfer_id, idx, addr, flags, length, data in self._xfer_reqs:
      # This option is not supported by the self._servo_i2c_bus interface.
      assert not flags & I2C_M_RECV_LEN
      if flags & I2C_M_RD:
        read_idx = idx
        read_count = length
        read_flags = flags
      else:
        write_idx = idx
        # TODO(b/79684405): This is silly, wr_rd() often/always converts back to
        #   byte array, i.e. Python 2 str / Python 3 bytes, using chr().  Update
        #   servo I2C bus interface to accept byte array.
        write_list = [ord(c) for c in data]
        write_flags = flags

    try:
      retval = self._servo_i2c_bus.wr_rd(addr, write_list, read_count)
    except (OSError, IOError) as error:
      self._logger.exception(
          'self._servo_i2c_bus.wr_rd() raised %s' % (error,))
      errnum = error.errno or 1

    writes = []
    if write_idx is not None:
      writes.append(_I2C_XFER_REPLY_FMT_STR % (
          xfer_id, write_idx, addr, write_flags, errnum))
      writes.append(_CMD_END_CHAR)

    if read_idx is not None:
      writes.append(_I2C_XFER_REPLY_FMT_STR % (
          xfer_id, read_idx, addr, read_flags, errnum))
      if retval:
        writes.append(_HEADER_SEP_CHAR)
        writes.append(_DATA_SEP_CHAR.join(b'%02X' % (b,) for b in retval))
      writes.append(_CMD_END_CHAR)

    if writes:
      self._device_write_queue.extend(writes)
      self._do_device_writes()

  def _cmd_i2c_xfer_req(self, line):
    """Queue an I2C transfer request.  Must already be in a transaction.

    Args:
      line: str - The I2C_XFER_REQ line read from the i2c-pseudo device.
    """
    assert self._in_tx

    xfer_id, idx, addr, flags, length = line.split(_HEADER_SEP_CHAR, 6)[1:6]
    xfer_id = int(xfer_id, base=0)
    idx = int(idx, base=0)
    addr = int(addr, base=0)
    flags = int(flags, base=0)
    length = int(length, base=0)

    if flags & I2C_M_RD:
      data = None
    else:
      parts = line.split(_HEADER_SEP_CHAR, 6)
      if len(parts) < 5:
        data = b''
      else:
        data = b''.join(
            chr(int(hex_, 16)) for hex_ in parts[6].split(_DATA_SEP_CHAR))
    self._xfer_reqs.append((xfer_id, idx, addr, flags, length, data))

  def _cmd_i2c_adap_num(self, line):
    """Record the I2C adapter number of this I2C pseudo controller.

    Args:
      line: str - The I2C_ADAPTER_NUM line read from the i2c-pseudo device.
    """
    self._i2c_adapter_num = int(line.split(_HEADER_SEP_CHAR, 2)[1])
    self._logger.info('I2C adapter number: %d' % (self._i2c_adapter_num,))

  def _cmd_i2c_pseudo_id(self, line):
    """Record the I2C pseudo ID of this I2C pseudo controller.

    Args:
      line: str - The I2C_PSEUDO_ID line read from the i2c-pseudo device.
    """
    self._i2c_pseudo_id = int(line.split(_HEADER_SEP_CHAR, 2)[1])
    self._logger.info('I2C pseudo ID: %d' % (self._i2c_pseudo_id,))

  def _do_ctrlr_cmd(self, line):
    """Dispatch an I2C pseudo controller command to the appropriate handler.

    Args:
      line: A full read command line from the i2c-pseudo controller device.
          Must NOT contain the commmand-terminating character (_CMD_END_CHAR).
    """
    if not line:
      return
    assert _CMD_END_CHAR not in line
    cmd_name = line.split(_HEADER_SEP_CHAR, 1)[0]
    if cmd_name == b'I2C_BEGIN_XFER':
      self._cmd_i2c_begin_xfer(line)
    elif cmd_name == b'I2C_COMMIT_XFER':
      self._cmd_i2c_commit_xfer(line)
    elif cmd_name == b'I2C_XFER_REQ':
      self._cmd_i2c_xfer_req(line)
    elif cmd_name == b'I2C_ADAPTER_NUM':
      self._cmd_i2c_adap_num(line)
    elif cmd_name == b'I2C_PSEUDO_ID':
      self._cmd_i2c_pseudo_id(line)
    else:
      self._logger.warn(
          'unrecognized I2C pseudo controller device command name %r' %
          (cmd_name,))

  def _do_device_reads(self):
    """Read commands from the controller fd.

    This is NOT thread-safe.  Do not make multiple concurrent calls to this.

    This will read until EOF or an error is returned.

    Returns:
      bool - True if EOF was encountered, False otherwise.
    """
    eof = False

    while True:
      try:
        data = os.read(self._device_fd, _READ_SIZE)
      except EOFError:
        eof = True
        break
      except (OSError, IOError) as error:
        if error.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
          break
        raise

      if not data:
        eof = True
        break

      while data:
        data_newline_idx = data.find(_CMD_END_CHAR)
        if data_newline_idx < 0:
          self._device_read_buffers.append(data)
          break
        self._device_read_buffers.append(data[:data_newline_idx])
        self._do_ctrlr_cmd(b''.join(self._device_read_buffers))
        del self._device_read_buffers[:]
        data = data[data_newline_idx + 1:]

    return eof

  def _do_device_writes(self):
    """Write all buffers in self._device_write_lock to controller fd.

    This is NOT guaranteed to empty self._device_write_queue.  This will return
    early if the write would block, or if EOF is encountered.

    Returns:
      bool - True if EOF was encountered, False otherwise.
    """
    eof = False

    with self._device_write_lock:
      while self._device_write_queue:
        data = self._device_write_queue.popleft()
        if not data:
          continue
        try:
          count = os.write(self._device_fd, data)
        # TODO(b/79684405): Should EOF i.e. zero return value from write(2) be
        # considered transient instead of permanent?
        except EOFError:
          eof = True
          break
        except (OSError, IOError) as error:
          if error.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            break
          raise
        if count <= 0:
          break
        if count < len(data):
          self._device_write_queue.appendleft(data[count:])

      # self._device_write_queue may still have items if we had to break from
      # the loop above.
      self._set_device_eventmask(
          _EPOLL_EVENTMASK_WITH_WRITES if self._device_write_queue else
          _EPOLL_EVENTMASK_NO_WRITES)

    return eof

  def _set_device_eventmask(self, eventmask):
    with self._device_eventmask_lock:
      if eventmask != self._device_epoll_eventmask:
        self._epoll.modify(self._device_fd, eventmask)
        self._device_epoll_eventmask = eventmask

  def _device_poll_handler(self, event):
    """Handle a poll event from the I2C pseudo controller device.

    Args:
      event: int - epoll event mask

    Returns:
      bool - True if EOF was encountered, False otherwise.
    """
    eof = False
    if event & _EPOLL_EVENTMASK_NO_WRITES:
      eof |= self._do_device_reads()
    if event & select.EPOLLOUT:
      eof |= self._do_device_writes()
    return eof

  def _io_thread_run(self):
    """Entry point for thread which handles all I2C pseudo controller I/O.

    This handles both I/O with i2c-pseudo kernel module, and I/O with the Servo
    I2C bus.  Those two sides of this controller could be split into separate
    threads, and the i2c-pseudo side could be further split into separate read
    and write threads, however any performance difference is likely minimal and
    would not justify the added complexity.
    """
    keep_looping = True
    while keep_looping:
      try:
        epoll_ret = self._epoll.poll()
      except (IOError, OSError) as error:
        # Python 3.5+ will retry after EINTR automatically, delete this after
        # upgrading.
        if error.errno == errno.EINTR:
          continue
        raise
      for fd, event in epoll_ret:
        if fd == self._device_fd:
          if self._device_poll_handler(event):
            keep_looping = False

  def _enqueue_simple_ctrlr_cmd(self, cmd_args):
    """Add a I2C pseudo controller write command to the write queue.

    Args:
      cmd_ags: iterable of bytes - The header fields of the command, and
          optional data field as final item.
    """
    self._device_write_queue.append(
        _HEADER_SEP_CHAR.join(cmd_args) + _CMD_END_CHAR)

  def shutdown(self, timeout):
    """Shutdown the I2C pseudo adapter.

    start() MUST NOT be called during or after this.

    Args:
      timeout: None, int, or float - Wait this many seconds for the I/O thread
          to complete, or None to wait indefinitely.  Use 0 or 0.0 to not wait.

    Returns:
      bool - True if the pseudo controller and its I/O thread stopped before
          expiration of the timeout, False otherwise.
    """
    with self._startstop_lock:
      started = self._started
      self._started = None

    if self._device_fd is not None:
      self._enqueue_simple_ctrlr_cmd((b'ADAPTER_SHUTDOWN',))
      self._do_device_writes()

    if not started:
      if self._device_fd is not None:
        try:
          os.close(self._device_fd)
        finally:
          self._device_fd = None

    if self._io_thread is None:
      return True

    if timeout is None or timeout > 0:
      self._io_thread.join(timeout=timeout)
    return not self._io_thread.is_alive()

  def __del__(self):
    self.shutdown(timeout=0)
