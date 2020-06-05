# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Instance tool to manage running instances."""

import os
import signal
import time

import servo.utils.scratch as scratch
import tool


class InstanceError(Exception):
  """Instance tool error class."""
  pass


def _format_info(info):
  """Output format helper that turns a dictionary into 'key: value' lines."""
  output_lines = ['%s : %s' % (val, info[val]) for val in ORDER]
  return '\n'.join(output_lines)


# order used to print information
ORDER = ['port', 'serials', 'pid']


PORT_RANGE = (9980, 9999)


class Instance(tool.Tool):
  """Class to implement various subtools to manage a servod instance."""

  # Minimum time in s to wait on a servod process to turn down gracefully before
  # attempting to send a SIGKILL instead.
  _SIGTERM_RETRY_TIMEOUT_S = 5
  # Wait period in s to when to wait before polling the servod process again.
  _SIGTERM_RETRY_WAIT_S = .1

  def __init__(self):
    """Setup scratch to use."""
    super(Instance, self).__init__()
    self._scratch = scratch.Scratch()

  @property
  def help(self):
    """Tool help message for parsing."""
    return 'Manage running servod instances.'

  def show(self, args):
    """Print info of servod instance found by -p/-s args."""
    try:
      entry = self._scratch.FindById(args.id)
      self._logger.info(_format_info(entry))
    except scratch.ScratchError as e:
      self.error(str(e))

  def show_all(self, _):
    """Print info of all registered servod instances."""
    output_lines = [_format_info(entry) for entry in
                    self._scratch.GetAllEntries()]
    if output_lines:
      self._logger.info('\n---\n'.join(output_lines))
    else:
      self._logger.info('No entries found.')

  def stop(self, args):
    """Stop servod instance found by -i/--identifier arg.

    Servod handles the cleanup code to remove its own entry.

    Args:
      args: args from cmdline argument with id attribute,
            id is either a port or serial number used to find servod scratch
            entry
    """
    try:
      entry = self._scratch.FindById(args.id)
      pid = entry['pid']
    except scratch.ScratchError as e:
      self._logger.info(str(e))
      return
    os.kill(pid, signal.SIGTERM)
    self._logger.info('SIGTERM sent to servod instance associated with id %r.',
                      args.id)
    end = time.time() + self._SIGTERM_RETRY_TIMEOUT_S
    try:
      while time.time() < end:
        os.kill(pid, 0)
        time.sleep(self._SIGTERM_RETRY_WAIT_S)
    except OSError:
      # This indicates the process has died and the job here is done
      self._logger.info('Servod instance associated with id %r turned down.',
                        args.id)
    else:
      # Getting here indicates the process did not die within the timeout. Bring
      # out a bigger hammer.
      self._logger.info('Servod instance associated with %r (pid %r) did not '
                        'turn down after SIGTERM. Sending SIGKILL.', args.id,
                        str(pid))
      os.kill(pid, signal.SIGKILL)
    finally:
      # Irrespective, the entry needs to be removed.
      self._scratch.RemoveEntry(args.id)

  def rebuild(self, args):
    """Rebuild servodscratch.

    If for some reason the scratch has gotten into a bad state, this can be used
    to attempt to rebuild entries. If |args.port| is a port, then attempt
    to specifically rebuild that port. Otherwise, attempt to rebuild each
    port in the default port range that is not a known entry.

    Args:
      args: parser namespace that should contain |port|,
            port is either None or a port number
    """
    known_ports = lambda entries: set(int(entry['port']) for entry in entries)
    if args.port:
      port = args.port
      if port in known_ports(self._scratch.GetAllEntries()):
        self._logger.info('port %r already known.', port)
      elif not self._scratch.GenerateEntryFromPort(port):
        self.error('Could not rebuild entry for port %r', port)
    # PORT_RANGE[1] + 1 as PORT_RANGE[1] should be in the set.
    ports = set(range(PORT_RANGE[0], PORT_RANGE[1] + 1))
    ports -= known_ports(self._scratch.GetAllEntries())
    for port in ports:
      # GenerateEntryFromPort will attempt to generate a new entry if
      # a ServoClient can be bound to |port|.
      self._scratch.GenerateEntryFromPort(port)

  def add_args(self, tool_parser):
    """Add the arguments needed for this tool."""
    subcommands = tool_parser.add_subparsers(dest='command')
    show = subcommands.add_parser('show',
                                  help='show information on servod instance')
    stop = subcommands.add_parser('stop',
                                  help='gracefully stop servod instance')
    # TODO(coconutruben): build out restart function
    for p in [show, stop]:
      id_group = p.add_mutually_exclusive_group(required=True)
      id_group.add_argument('-s', '--serial', dest='id',
                            help='serial of servo device on associated servod.')
      id_group.add_argument('-p', '--port', dest='id', type=int,
                            help='port where servod instance is listening.')
    rebuild = subcommands.add_parser('rebuild', help='try to rebuild entry for '
                                     'servod running on a given port. If no '
                                     'specific port provided, attempts default '
                                     'servod port range.')
    rebuild.add_argument('-p', '--port', default=None, type=int,
                         help='port to rebuild.')
    subcommands.add_parser('show-all', help='show info on all servod instances')
