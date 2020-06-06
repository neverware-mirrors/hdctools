# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility to manage information about different instances."""

import json
import logging
import os
import socket

import servo.client as client

SERVO_SCRATCH_DIR = '/tmp/servoscratch'


class ScratchError(Exception):
  """Error class for servo scratch utility."""


class Scratch(object):
  """Class to manage servod instance breadcrumbs used to query and control.

  Attributes:
    _logger: logger
    _scratch: directory to leave information in.
  """

  _NO_FOUND_WARNING = 'No servod scratch entry found under id: %r.'

  def __init__(self, scratch=SERVO_SCRATCH_DIR):
    """Initialize utility by creating |scratch| if necessary.

    Args:
      scratch: directory to write servod info into.

    Note:
      Unless for good reason (test, special setup) scratch should be left as
      its default.
    """
    self._dir = scratch
    self._logger = logging.getLogger(type(self).__name__)
    if not os.path.exists(self._dir):
      os.makedirs(self._dir)
    self._Sanitize()

  def _EntryF(self, entry):
    """Generate a filename for |entry|."""
    return os.path.join(self._dir, str(entry['port']))

  def AddEntry(self, port, serials, pid):
    """Register information about servod instance.

    Args:
      port: port servod is being served
      serials: list of serialnames for devices being served through instance
      pid: pid of the main servod process

    Raises:
      ScratchError: if port or pid aren't int convertible or serials isn't
      list convertible, if port or any serial in serials already has an entry
    """
    # TODO(coconutruben): add cmdline support
    try:
      entry = {'port': int(port),
               'serials': list(serials),
               'pid': int(pid),
               'active': False}
    except (ValueError, TypeError):
      raise ScratchError('Entry arguments malformed.')
    entryf = self._EntryF(entry)
    if os.path.exists(entryf):
      msg = 'Adding entry for port already in use. Port: %d.' % int(port)
      self._logger.error(msg)
      raise ScratchError(msg)
    serialfs = []
    for serial in entry['serials']:
      serialf = os.path.join(self._dir, str(serial))
      if os.path.exists(serialf):
        # Add a symlink for each serial pointing back at the original file
        msg = ('Adding entry in %s for serial already in use. Serial: %s.'
               % (serialf, serial))
        self._logger.error(msg)
        raise ScratchError(msg)
      serialfs.append(serialf)

    self._WriteEntry(entry)

    # Add the symlinks as well.
    for serialf in serialfs:
      os.symlink(os.path.basename(entryf), serialf)

  def RemoveEntry(self, identifier):
    """Remove information about servod instance.

    Args:
      identifier: either port where servod is being served, or a serial number
                  of one of the servod devices being served by instance
    """
    entryf = os.path.realpath(os.path.join(self._dir,
                                           str(identifier)))
    if not os.path.exists(entryf):
      self._logger.warn('No entry available for id: %s. Ignoring.', identifier)
      return
    for f in os.listdir(self._dir):
      fullf = os.path.join(self._dir, f)
      if os.path.islink(fullf) and os.path.realpath(fullf) == entryf:
        os.remove(fullf)
    os.remove(entryf)

  def MarkActive(self, identifier):
    """Mark entry at |identifier| as active."""
    entry = self.FindById(identifier)
    if entry['active']:
      self._logger.info('Entry at %r already marked active.')
    else:
      entry['active'] = True
      self._WriteEntry(entry)

  def _WriteEntry(self, entry):
    """Write entry to file."""
    entryf = self._EntryF(entry)
    with open(entryf, 'w') as f:
      json.dump(entry, f)

  def GetAllEntries(self):
    """Find and load servod instance info for all registered servod instances.

    Returns:
      List of dictionaries containing 'port', 'serials', and 'pid' of instance
    """
    entries = []
    for f in os.listdir(self._dir):
      entryf = os.path.join(self._dir, f)
      if os.path.islink(entryf):
        continue
      with open(entryf, 'r') as f:
        try:
          entries.append(json.load(f))
        except ValueError:
          self._logger.warn('Removing file %r as it contains invalid JSON.',
                            entryf)
          # Invalid json file
          os.remove(entryf)
    return entries

  def GenerateEntryFromPort(self, port):
    """Given a port number, try to generate an entry from it.

    Tries to ask servod instance for information to retroactively
    add an entry.

    Args:
      port: port where the alleged servod instance is listening

    Returns:
      True if entry successfully rebuilt, False otherwise
    """
    # pylint: disable=protected-access
    msg = 'nonsense'
    expected_output = 'ECH0ING: %s' % msg
    try:
      sclient = client.ServoClient(port=port)
      if sclient._server.echo(msg) == expected_output:
        self._logger.warn('Port %r not registered but has a servod '
                          'instance bound to it. Retroactively adding the '
                          'instance.', port)
        serials = sclient._server.get_servo_serials()
        # The serials have to be unique. Enforce this here by creating a set
        serials = list(set(serials.values()))
        pid = sclient.get('servod_pid')
        self.AddEntry(port=port, serials=serials, pid=pid)
        return True
    except socket.error:
      # expected to fail as no servod instance should be running on an
      # untracked port.
      return False
    except ScratchError:
      # Don't rebuild an entry if the entry already exists.
      return False

  def FindById(self, identifier):
    """Find and load servod instance info for identifier.

    Args:
      identifier: either port where servod is being served, or a serial number
                  of one of the servod devices being served by instance

    Returns:
      dictionary containing 'port', 'serials', and 'pid' of instance

    Raises:
      ScratchError: if no entry found under |indentifier| or if entry found
                    is invalid json
    """
    entryf = os.path.join(self._dir, str(identifier))
    if not os.path.exists(entryf):
      raise ScratchError(self._NO_FOUND_WARNING % identifier)
    with open(entryf, 'r') as f:
      try:
        entry = json.load(f)
      except ValueError:
        # Invalid json file
        os.remove(entryf)
        raise ScratchError('id: %s had invalid json formatting. Removed.' %
                           identifier)
    return entry

  def _Sanitize(self):
    """Verify that all known servod ports are still in use, delete otherwise."""
    for entry in self.GetAllEntries():
      testsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      port = entry['port']
      try:
        testsock.bind(('localhost', port))
        self._logger.warn('Port %r still registered but not bound to a '
                          'servod instance. Removing entry.', str(port))
        self.RemoveEntry(port)
        testsock.close()
      except socket.error:
        # Expected to fail when binding to a valid servod instance socket.
        pass
