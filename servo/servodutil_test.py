# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import shutil
import socket
import tempfile
import unittest

import servodutil


class TestServoScratch(unittest.TestCase):

  def setUp(self):
    """Setup each test.

    Prepare a ServoScratch on a temp directory & prepare a convenience entry.
    """
    self._scratchdir = tempfile.mkdtemp()
    self._scratch = servodutil.ServoScratch(self._scratchdir)
    self._dport = 31234
    self._dserials = ['9', '17']
    self._dpid = 1827
    # Commonly used test entry
    self._entry = {'pid': self._dpid,
                   'serials': self._dserials,
                   'port': self._dport}

  def tearDown(self):
    """Remove entry directory structure created during the test."""
    shutil.rmtree(self._scratchdir)

  def test_Init(self):
    """Verify servodutil creates the directory if it doesn't exist."""
    new_scratchdir = os.path.join(self._scratchdir, 'testdir')
    assert not os.path.exists(new_scratchdir)
    # Only initialize the servodutil to ensure it creates |new_scratchdir|
    servodutil.ServoScratch(new_scratchdir)
    assert os.path.exists(new_scratchdir)
    os.rmdir(new_scratchdir)

  def test_AddEntry(self):
    """AddEntry creates & saves entry, and makes symlinks for each serial."""
    self._scratch.AddEntry(port=self._dport, serials=self._dserials,
                           pid=self._dpid)
    # Ensure port entry created
    port_entry = os.path.join(self._scratchdir, str(self._dport))
    assert os.path.exists(port_entry)
    for serial in self._dserials:
      serial_entry = os.path.join(self._scratchdir, serial)
      # Ensure serial number entry created
      assert os.path.exists(serial_entry)
      # Ensure serial number entry is a link
      assert os.path.islink(serial_entry)
      # Ensure serial number entry is a link to the port entry
      assert os.path.realpath(serial_entry) == port_entry
    # Load entry
    with open(port_entry, 'r') as entryf:
      entry = json.load(entryf)
    # Compare entry loaded with entry saved
    assert entry == {'pid': self._dpid,
                     'serials': self._dserials,
                     'port': self._dport}

  def test_AddEntryNonNumericalPort(self):
    """Verify AddEntry raises ServodUtilError when port can't be cast to int."""
    port = 'hello'
    with self.assertRaises(servodutil.ServodUtilError):
      self._scratch.AddEntry(port, self._dserials, self._dpid)

  def test_AddEntryNonNumericalPID(self):
    """Verify AddEntry raises ServodUtilError when pid can't be cast to int."""
    pid = 'hello'
    with self.assertRaises(servodutil.ServodUtilError):
      self._scratch.AddEntry(self._dport, self._dserials, pid)

  def test_AddEntryNonListlikeSerials(self):
    """Verify AddEntry raises ServodUtilError when serials is not iterable."""
    serials = 17
    with self.assertRaises(servodutil.ServodUtilError):
      self._scratch.AddEntry(self._dport, serials, self._dpid)

  def test_AddEntryTwice(self):
    """Verify AddEntry raises ServodUtilError when adding same entry twice."""
    self._scratch.AddEntry(port=self._dport, serials=self._dserials,
                           pid=self._dpid)
    # Ensure error when adding the same entry twice
    with self.assertRaises(servodutil.ServodUtilError):
      self._scratch.AddEntry(port=self._dport, serials=self._dserials,
                             pid=self._dpid)

  # TODO(coconutruben): flesh out more to test equal port, equal serial,
  # and potentially equal pid individually.

  def _manually_add_entry(self, entry=None):
    """Manually add an entry. Uses self._entry if no entry supplied."""
    if not entry:
      entry = self._entry
    files_added = []
    entryfn = os.path.join(self._scratchdir, str(entry['port']))
    # Manually add an entry and the symlinks
    with open(entryfn, 'w') as entryf:
      json.dump(entry, entryf)
      files_added.append(entryfn)
    for serial in entry['serials']:
      linkfn = os.path.join(self._scratchdir, str(serial))
      os.symlink(entryfn, linkfn)
      files_added.append(linkfn)
    return files_added

  def test_RemoveEntry(self):
    """Verify RemoveEntry removes an entry fully (file + symlinks)."""
    scratch = self._scratchdir
    port = '9809'
    serials = ['8000', '237300', 'lolaserial']
    entry2 = {'pid': self._dpid,
              'serials': serials,
              'port': port}
    entry_files = set(self._manually_add_entry())
    entry2_files = set(self._manually_add_entry(entry2))
    # Ensure there's a file for each serial, and one for the port
    scratch_files = set([os.path.join(scratch, f) for f in os.listdir(scratch)])
    assert scratch_files == (entry_files | entry2_files)
    self._scratch.RemoveEntry(port)
    # Ensure all files are removed
    scratch_files = set([os.path.join(scratch, f) for f in os.listdir(scratch)])
    assert scratch_files == entry_files
    # Ensure the right files were removed
    assert not os.path.exists(os.path.join(self._scratchdir, port))
    for serial in serials:
      assert not os.path.exists(os.path.join(self._scratchdir, serial))

  def test_RemoveEntryBadIdentifier(self):
    """Verify RemoveEntry quietly ignores removing an unknown identifier."""
    self._manually_add_entry()
    self._scratch.RemoveEntry('badid')

  def test_FindByIdPort(self):
    """Verify FindById works using ports."""
    self._manually_add_entry()
    entry_from_file = self._scratch.FindById(self._dport)
    assert entry_from_file == self._entry

  def test_FindByIdSerial(self):
    """Verify FindById works using serials."""
    self._manually_add_entry()
    for serial in self._dserials:
      entry_from_file = self._scratch.FindById(serial)
      assert entry_from_file == self._entry

  def test_FindByIdBadJSON(self):
    """Verify FindById raises ServodUtilError when id points to invalid JSON."""
    identifier = 'nonsense'
    entryfn = os.path.join(self._scratchdir, identifier)
    with open(entryfn, 'w') as entryf:
      entryf.write('This is not JSON')
    assert os.path.exists(entryfn)
    with self.assertRaises(servodutil.ServodUtilError):
      self._scratch.FindById(identifier)
    # FindById removes invalid json files
    assert not os.path.exists(entryfn)

  def test_FindByIdBadId(self):
    """Verify FindById raises ServodUtilError when using an unknown id."""
    self._manually_add_entry()
    with self.assertRaises(servodutil.ServodUtilError):
      self._scratch.FindById('badid')

  def test_GetAllEntriesEmpty(self):
    """Verify GetAllEntries() doesn't break when there are no entries."""
    # pylint: disable=g-explicit-bool-comparison
    assert self._scratch._GetAllEntries() == []

  def test_GetAllEntries(self):
    """Verify GetAllEntries() retrives all entries."""
    # Dictionary to hold entries added
    mentries = {}
    mentries[9999] = {'port': 9999, 'serials': ['1999'], 'pid': 1234}
    mentries[9998] = {'port': 9998, 'serials': ['1998'], 'pid': 1235}
    mentries[9997] = {'port': 9997, 'serials': ['1997'], 'pid': 1236}
    self._manually_add_entry(mentries[9999])
    self._manually_add_entry(mentries[9998])
    self._manually_add_entry(mentries[9997])
    entries = self._scratch._GetAllEntries()
    assert len(entries) == len(mentries)
    for entry in entries:
      assert mentries[entry['port']] == entry

  def test_SanitizeNothingToDo(self):
    """Verify Sanitize does not remove active scratch entry."""
    self._manually_add_entry()
    testsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    testsock.bind(('localhost', self._dport))
    prevfiles = os.listdir(self._scratchdir)
    self._scratch._Sanitize()
    postfiles = os.listdir(self._scratchdir)
    # Port is attached so Sanitize should not wipe the entry
    assert prevfiles == postfiles
    testsock.close()

  def test_SanitizeStaleEntry(self):
    """Verify that stale entries in servoscratch are removed."""
    self._manually_add_entry()
    self._scratch._Sanitize()
    # The port is likely not connected to anything so Sanitize should consider
    # this a stale entry and remove it.
    assert not os.listdir(self._scratchdir)

  def test_SanitizeMultipleStaleEntry(self):
    """Verify that stale entries in servoscratch are removed."""
    self._manually_add_entry()
    entry2 = {'pid': 12345,
              'serials': ['this-is-not-a-serial'],
              'port': 9888}
    self._manually_add_entry(entry2)
    self._scratch._Sanitize()
    # The ports are  likely not connected to anything so Sanitize should
    # consider these stale entries and remove them.
    assert not os.listdir(self._scratchdir)

  def test_ConvertNameToMethodNoCamel(self):
    """Verify that strings without '-' only get capitalized."""
    name = 'hi'
    assert servodutil._ConvertNameToMethod(name) == 'Hi'

  def test_ConvertNameToMethodDoubleCamel(self):
    """Verify proper camel-case conversion for strings containing '-'."""
    name = 'hi-there-friends'
    assert servodutil._ConvertNameToMethod(name) == 'HiThereFriends'

if __name__ == '__main__':
  unittest.main()
