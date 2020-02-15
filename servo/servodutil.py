# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Collection of servod utilities."""

import argparse
import logging
import os
import signal
import sys
import time

import utils.scratch as scratch


def _FormatInfo(info):
  """Output format helper that turns a dictionary into 'key: value' lines."""
  output_lines = ['%s : %s' % (val, info[val]) for val in ORDER]
  return '\n'.join(output_lines)


# order used to print information
ORDER = ['port', 'serials', 'pid']


PORT_RANGE = (9980, 9999)


class ServodUtilError(Exception):
  """General servodutil error class."""
  pass


class Instance(object):
  """Class to implement various tools to manage a servod instance."""

  # Minimum time in s to wait on a servod process to turn down gracefully before
  # attempting to send a SIGKILL instead.
  _SIGTERM_RETRY_TIMEOUT_S = 5
  # Wait period in s to when to wait before polling the servod process again.
  _SIGTERM_RETRY_WAIT_S = .1

  def __init__(self):
    """Setup scratch to use."""
    self._logger = logging.getLogger(type(self).__name__)
    self._scratch = scratch.Scratch()

  def Show(self, args):
    """Print info of servod instance found by -p/-s args."""
    try:
      entry = self._scratch.FindById(args.id)
      self._logger.info(_FormatInfo(entry))
    except scratch.ScratchError as e:
      self._logger.info(str(e))

  def ShowAll(self, _):
    """Print info of all registered servod instances."""
    output_lines = [_FormatInfo(entry) for entry in
                    self._scratch.GetAllEntries()]
    if output_lines:
      self._logger.info('\n---\n'.join(output_lines))
    else:
      self._logger.info('No entries found.')

  def Stop(self, args):
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
    while time.time() < end:
      try:
        os.kill(pid, 0)
      except OSError:
        # This indicates the process has died and the job here is done
        self._logger.info('Servod instance associated with id %r turned down.',
                          args.id)
        return
      time.sleep(self._SIGTERM_RETRY_WAIT_S)
    # Getting here indicates the process did not die within the timeout. Bring
    # out a bigger hammer.
    self._logger.info('Servod instance associated with %r (pid %r) did not '
                      'turn down after SIGTERM. Sending SIGKILL.', args.id,
                      str(pid))
    os.kill(pid, signal.SIGKILL)

  def Rebuild(self, args):
    """Rebuild servodscratch.

    If for some reason the scratch has gotten into a bad state, this can be used
    to attempt to rebuild entries. If |args.port| is a port, then attempt
    to specifically rebuild that port. Otherwise, attempt to rebuild each
    port in the default port range that is not a known entry.

    Args:
      args: parser namespace that should contain |port|,
            port is either None or a port number
    """
    def known_ports():
      # pylint: disable=invalid-name
      return set(int(entry['port']) for
                 entry in self._scratch.GetAllEntries())
    if args.port:
      port = args.port
      if port in known_ports():
        self._logger.info('port %r already known.', port)
      elif not self._scratch.GenerateEntryFromPort(port):
        self._logger.error('Could not rebuild entry for port %r', port)
      return
    # PORT_RANGE[1] + 1 as PORT_RANGE[1] should be in the set.
    ports = set(range(PORT_RANGE[0], PORT_RANGE[1] + 1))
    ports -= known_ports()
    for port in ports:
      # GenerateEntryFromPort will attempt to generate a new entry if
      # a ServoClient can be bound to |port|.
      self._scratch.GenerateEntryFromPort(port)


# pylint: disable=invalid-name
def _ConvertNameToMethod(name):
  """Convert dash separated words to camelcase."""
  parts = name.split('-')
  return ''.join([w.capitalize() for w in parts])


# pylint: disable=dangerous-default-value
def main(cmdline=sys.argv[1:]):
  """Entry function for cmdline servodutil tool."""
  # pylint: disable=protected-access
  root_logger = logging.getLogger()
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.INFO)
  root_logger.setLevel(logging.DEBUG)
  root_logger.addHandler(stdout_handler)
  instances = Instance()
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(dest='command')
  show = subparsers.add_parser('show',
                               help='show information on servod instance')
  stop = subparsers.add_parser('stop',
                               help='gracefully stop servod instance')
  # TODO(coconutruben): build out restart function
  for p in [show, stop]:
    id_group = p.add_mutually_exclusive_group(required=True)
    id_group.add_argument('-s', '--serial', dest='id',
                          help='serial of servo device on associated servod.')
    id_group.add_argument('-p', '--port', dest='id', type=int,
                          help='port where servod instance is listening.')
  rebuild = subparsers.add_parser('rebuild', help='try to rebuild entry for '
                                  'servod running on a given port. If no '
                                  'specific port provided, attempts default '
                                  'servod port range.')
  rebuild.add_argument('-p', '--port', default=None, type=int,
                       help='port to rebuild.')
  subparsers.add_parser('show-all', help='show info on all servod instances')
  args = parser.parse_args(cmdline)
  cmd = _ConvertNameToMethod(args.command)
  getattr(instances, cmd)(args)

if __name__ == '__main__':
  main()
