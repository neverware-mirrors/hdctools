# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for the logic inside servo_parsing."""

import copy
import os
import shutil
import socket
import tempfile
import unittest

import client
import servo_parsing
import servodutil

# Throughout all the tests in this file, parse_known_args is used instead of
# parse args. This is to avoid having to clutter the tests with unrelated
# cmdline options.


class TestRCFile(unittest.TestCase):
  """Test RC file parsing logic, with emphasis on error handling."""

  @staticmethod
  def CreateFakeRCFile(name, serial, board=None, model=None, tempdir=None):
    """Helper to create a fake RC file with one entry based on args."""
    if not tempdir:
      tempdir = tempfile.mkdtemp()
    rc_file = os.path.join(tempdir, 'rc')
    with open(rc_file, 'w') as f:
      # 0 as PORT is no longer supported, but the slot is still there for
      # legacy reasons.
      entry_pieces = [name, serial, '0']
      if board:
        entry_pieces.append(board)
        if model:
          # Only add model if board is also given.
          entry_pieces.append(model)
      entry = '%s\n' % ', '.join(entry_pieces)
      f.write(entry)
    return rc_file

  def setUp(self):
    """Prepare cmdline, and a fake RC file to test RC file parsing."""
    # create a fake RC file
    unittest.TestCase.setUp(self)
    self._name = 'Alfred'
    self._serialname = 'this-is-a-fake-serial'
    self._board = 'fake-board'
    self._rc_file = TestRCFile.CreateFakeRCFile(name=self._name,
                                                serial=self._serialname,
                                                board=self._board)
    self._cmdline = ['--name', self._name]

  def tearDown(self):
    """Delete the temporary directory and its content."""
    shutil.rmtree(os.path.dirname(self._rc_file))
    unittest.TestCase.tearDown(self)

  def test_NormalRCFile(self):
    """A well configured RC file generates the expected rc dictionary."""
    rcd = servo_parsing.ServodRCParser.ParseRC(self._rc_file)
    assert self._name in  rcd
    rcd_entry = rcd[self._name]
    assert self._serialname == rcd_entry['sn']
    assert self._board == rcd_entry['board']

  def test_NoRCFile(self):
    """Passed in RC file does not exist: return empty runtime config dict."""
    rcd = servo_parsing.ServodRCParser.ParseRC('/tmp/this-is-a-fake-file')
    # pylint: disable=g-explicit-bool-comparison
    # Expected return value is {} so this seems appropiate regardless of python
    # internals
    assert {} == rcd

  def test_RCFileMisconfigured(self):
    """RC file is misconfigured (no commas): return empy runtime config dict."""
    with open(self._rc_file, 'w') as f:
      # Extra space is just for padding
      f.write('%s %s %s %s      \n' % (self._name, self._serialname, '0',
                                       self._board))
    rcd = servo_parsing.ServodRCParser.ParseRC(self._rc_file)
    # pylint: disable=g-explicit-bool-comparison
    # Expected return value is {} so this seems appropiate regardless of python
    # internals
    assert {} == rcd


class TestServodRCParser(unittest.TestCase):
  """Test ServodRCParser substitution and overwrite logic."""

  def setUp(self):
    """Setup cmdline args, create fake RC file, and setup parser for tests."""
    unittest.TestCase.setUp(self)
    self._invalid_name = 'NotAlfred'
    self._valid_name = 'Alfred'
    self._serialname = 'this-is-a-fake-serial'
    self._board = 'fake-board'
    self._rc_file = TestRCFile.CreateFakeRCFile(name=self._valid_name,
                                                serial=self._serialname,
                                                board=self._board)
    self._original_env = copy.deepcopy(os.environ)
    # Overwite default file to use the test's rc file
    self._original_rc = servo_parsing.DEFAULT_RC_FILE
    servo_parsing.DEFAULT_RC_FILE = self._rc_file
    self.SetupParser()

  def SetupParser(self):
    """Helper to add parser."""
    self._parser = servo_parsing.ServodRCParser()
    # The default ServodRC parser does not have --board argument as this is
    # not relevant for servod clients. Add it here to test some board logic.
    self._parser.add_argument('-b', '--board', type=str)

  def tearDown(self):
    """Remove fake RC file and restore the os environment variables."""
    shutil.rmtree(os.path.dirname(self._rc_file))
    os.environ = self._original_env
    servo_parsing.DEFAULT_RC_FILE = self._original_rc
    unittest.TestCase.tearDown(self)

  def test_EnvNameNoSerialNoName(self):
    """Name defined in environment, no serial, no name: take name from env."""
    os.environ[servo_parsing.NAME_ENV_VAR] = self._valid_name
    # Regenerate the parser as this test modifies the os.environ map.
    self.SetupParser()
    cmdline = []
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._serialname == opts.serialname

  def test_EnvNameSerialNoName(self):
    """Name defined in environment, serial, no name: honor serial."""
    os.environ[servo_parsing.NAME_ENV_VAR] = self._valid_name
    # Regenerate the parser as this test modifies the os.environ map.
    self.SetupParser()
    cmdline = ['--serialname', self._serialname]
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._serialname == opts.serialname

  def test_EnvNameNoSerialNameInCmdline(self):
    """Name defined in environment, serial, name: honor cmdline name."""
    os.environ[servo_parsing.NAME_ENV_VAR] = self._invalid_name
    # Regenerate the parser as this test modifies the os.environ map.
    self.SetupParser()
    cmdline = ['--name', self._valid_name]
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._serialname == opts.serialname

  def test_NameSerial(self):
    """Serial and name defined: raise an error."""
    cmdline = ['--name', self._valid_name, '--serialname', self._serialname]
    with self.assertRaisesRegexp(SystemExit, '2'):
      _ = self._parser.parse_known_args(cmdline)

  def test_NameNoSerialBoard(self):
    """Name, and board defined: name maps to serial but no board overwrite."""
    new_board = 'new-board'
    cmdline = ['--name', self._valid_name, '--board', new_board]
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._serialname == opts.serialname
    assert new_board == opts.board

  def test_NameNoSerialNoBoard(self):
    """Only name defined: name maps to serial and adds board."""
    cmdline = ['--name', self._valid_name]
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._serialname == opts.serialname
    assert self._board == opts.board

  def test_NameNotInRCNoSerial(self):
    """Name is provided but no in RC: SystmExit from the parser."""
    cmdline = ['--name', self._invalid_name]
    with self.assertRaisesRegexp(servo_parsing.ServodParserError,
                                 'Name %r not in rc' % self._invalid_name):
      _ = self._parser.parse_known_args(cmdline)

  def test_NoNameSerialInRCNoBoard(self):
    """Serial shows up in the RC, & no board specified: take the rc's board."""
    cmdline = ['--serialname', self._serialname]
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._board == opts.board


class TestServodClientParser(unittest.TestCase):
  """Test ServoScratch based routing in ServodClientParser."""

  def setUp(self):
    """Create fake scratch entry, and setup cmdline args for tests."""
    unittest.TestCase.setUp(self)
    self._original_env = copy.deepcopy(os.environ)
    # The tests that want to manipulate the environment will do so themselves.
    # Thus, remove potential environments from the directory the test is being
    # run in.
    for env_var in [servo_parsing.PORT_ENV_VAR, servo_parsing.NAME_ENV_VAR]:
      if env_var in os.environ:
        del os.environ[env_var]
    self._scratchdir = tempfile.mkdtemp()
    self._scratch = servodutil.ServoScratch(self._scratchdir)
    self._scratchport = 12345
    self._serial = 'this-is-a-fake-serial'
    self._invalid_serial = 'this-is-an-invalid-fake-serial'
    # PID not stored as a variable as it's not part of the test.
    self._scratch.AddEntry(port=self._scratchport,
                           serials=[self._serial],
                           pid=1234)
    self.SetupParser()
    # Bind a fake socket to the port to avoid the ServoScratch from
    # cleaning up this invalid entry when the parser initializes it.
    self._rc_name = 'valid_name'
    self._rc_file = TestRCFile.CreateFakeRCFile(name=self._rc_name,
                                                serial=self._serial,
                                                board='fake-board')
    # Overwite default file to use the test's rc file
    self._original_rc = servo_parsing.DEFAULT_RC_FILE
    servo_parsing.DEFAULT_RC_FILE = self._rc_file
    self._fakesock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._fakesock.bind(('localhost', self._scratchport))

  def SetupParser(self):
    """Helper to add parser."""
    self._parser = servo_parsing.ServodClientParser(scratch=self._scratchdir)

  def tearDown(self):
    """Remove fake scratch entry, and close fake socket."""
    shutil.rmtree(os.path.dirname(self._rc_file))
    shutil.rmtree(self._scratchdir)
    servo_parsing.DEFAULT_RC_FILE = self._original_rc
    self._fakesock.close()
    os.environ = self._original_env
    unittest.TestCase.tearDown(self)

  def test_NoPortSerial(self):
    """No port but serialname in cmdline: look for the port in scratch."""
    cmdline = ['--serialname', self._serial]
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._scratchport == opts.port

  def test_EnvPortSerial(self):
    """Env port and serialname in cmdline: look for the port in scratch."""
    os.environ[servo_parsing.PORT_ENV_VAR] = '1782'
    # Regenerate the parser as this test modifies the os.environ map.
    self.SetupParser()
    cmdline = ['--serialname', self._serial]
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._scratchport == opts.port

  def test_EnvPortInvalidEnvName(self):
    """Env port and unknown name. An error is expected."""
    os.environ[servo_parsing.PORT_ENV_VAR] = str(self._scratchport)
    rc_name = 'random_name'
    os.environ[servo_parsing.NAME_ENV_VAR] = rc_name
    # Regenerate the parser as this test modifies the os.environ map.
    self.SetupParser()
    cmdline = []
    with self.assertRaisesRegexp(servo_parsing.ServodParserError,
                                 'Name %r not in rc' % rc_name):
      _ = self._parser.parse_known_args(cmdline)

  def test_EnvPortValidEnvNameInScratch(self):
    """Env port and known name. Name is used to lookup port in scratch."""
    port = '912749'
    # This port should not be used as a known name is provided that has a
    # scratch entry.
    os.environ[servo_parsing.PORT_ENV_VAR] = port
    os.environ[servo_parsing.NAME_ENV_VAR] = self._rc_name
    # Regenerate the parser as this test modifies the os.environ map.
    self.SetupParser()
    cmdline = []
    opts, _ = self._parser.parse_known_args(cmdline)
    assert self._scratchport == opts.port

  def test_EnvPortValidEnvNameNotInScratch(self):
    """Env port and known name that is not in scratch. Throw error."""
    # Removing the scratch entry so that the port lookup fails.
    self._scratch.RemoveEntry(self._scratchport)
    port = '912749'
    # This port should be used as an unknown name is provided that does not
    # have a scratch entry.
    os.environ[servo_parsing.PORT_ENV_VAR] = port
    os.environ[servo_parsing.NAME_ENV_VAR] = self._rc_name
    # Regenerate the parser as this test modifies the os.environ map.
    self.SetupParser()
    cmdline = []
    with self.assertRaisesRegexp(SystemExit, '2'):
      _ = self._parser.parse_known_args(cmdline)

  def test_NoPortNoSerial(self):
    """No port and no serialname in cmdline: revert to default port."""
    cmdline = []
    opts, _ = self._parser.parse_known_args(cmdline)
    assert client.DEFAULT_PORT == opts.port

  def test_NoPortSerialNoDutOnSerial(self):
    """No port and serialname in cmdline, serialname not in scratch: error."""
    cmdline = ['--serialname', self._invalid_serial]
    # Argparse raises sys.exit(2) on error.
    with self.assertRaisesRegexp(SystemExit, '2'):
      _ = self._parser.parse_known_args(cmdline)

if __name__ == '__main__':
  unittest.main()
