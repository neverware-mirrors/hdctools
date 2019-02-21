# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servod's logging handler works as intended."""

import hashlib
import logging
import os
import shutil
import tempfile
import unittest

import servo_logging

# There are 3 files that are exempt from the backup count.
# - the timestamp file
# - the open, uncompressed logfile
# - the 'latest' symbolic link
BACKUP_COUNT_EXEMPT_FILES = 3


def get_file_md5sum(path):
  """Return the md5 checksum of the file at |path|."""
  with open(path, 'rb') as f:
    return hashlib.md5(f.read()).hexdigest()


def get_rolled_fn(logfile, rotations):
  """Helper to get filename of |logfile| after |rotations| log rotations."""
  return '%s.%d.%s' % (logfile, rotations, servo_logging.COMPRESSION_SUFFIX)


class TestServodRotatingFileHandler(unittest.TestCase):

  # These are module wide attributs to cache and restore after tests
  # in case the tests wish to modify them.
  MODULE_ATTRS = ['MAX_LOG_BYTES',  # Max bytes a log file can grow to.
                  'LOG_BACKUP_COUNT',  # Number of rotated logfiles to keep.
                  'COMPRESSION_SUFFIX',  # Filetype suffix for compressed logs.
                  'LOG_DIR_PREFIX',  # Servo port log directory prefix.
                  'LOG_FILE_PREFIX',  # Log file name.
                  'TS_FILE',  # File name to cache the instance's timestamp.
                  'TS_FORMAT',  # Format string to for timestamps.
                  'TS_MS_FORMAT']  # Format string for timestamp millisecond
                                   # component.

  def setUp(self):
    """Set up data, create logging directory, cache module data."""
    unittest.TestCase.setUp(self)
    self.logdir = tempfile.mkdtemp()
    self.port = 9999
    self.test_logger = logging.getLogger('Test')
    self.test_logger.setLevel(logging.DEBUG)
    self.test_logger.propagate = False
    self.module_defaults = {}
    # Cache the module wide attributs to restore them after each test again.
    for attr in self.MODULE_ATTRS:
      self.module_defaults[attr] = getattr(servo_logging, attr)

  def tearDown(self):
    """Delete logging directory, remove handlers,restore module data."""
    shutil.rmtree(self.logdir)
    unittest.TestCase.tearDown(self)
    self.test_logger.handlers = []
    # Restore cached module attributes.
    for attr, val in self.module_defaults.iteritems():
      setattr(servo_logging, attr, val)

  def _installFH(self, fh):
    # pylint: disable=invalid-name
    # conform to standard unittest method naming.
    """Helper to install |fh| to |self.test_logger|."""
    fh.setLevel(logging.DEBUG)
    fh.formatter = logging.Formatter(fmt='')
    self.test_logger.addHandler(fh)

  def test_LoggerLogsToFile(self):
    """Basic sanity that content is being output to the file."""
    test_str = 'This is a test string to make sure there is logging.'
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      port=self.port)
    self._installFH(handler)
    self.test_logger.info(test_str)
    with open(handler.baseFilename, 'r') as log:
      assert log.read().strip() == test_str

  def test_RotationOccursWhenFileGrowsTooLarge(self):
    """Growing log-file beyond limit causes a rotation."""
    test_max_log_bytes = 40
    setattr(servo_logging, 'MAX_LOG_BYTES', test_max_log_bytes)
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      port=self.port)
    self._installFH(handler)
    # The first log is only 20 bytes and should not cause rotation.
    log1 = 'Here are 20 bytes la'
    # The second log is 40 bytes and should cause rotation.
    log2 = 'This is an attempt to make 40 bytes laaa'
    self.test_logger.info(log1)
    # No rolling should have occured yet.
    assert not os.path.exists(get_rolled_fn(handler.baseFilename, 1))
    # Rolling should have occured by now.
    self.test_logger.info(log2)
    assert os.path.exists(get_rolled_fn(handler.baseFilename, 1))

  def test_DeleteMultiplePastBackupCount(self):
    """No more than backup count logs are kept."""
    # Set the backup count to only be 3 for this test.
    new_backup_count = 3
    setattr(servo_logging, 'LOG_BACKUP_COUNT', new_backup_count)
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      port=self.port)
    for _ in range(2 * new_backup_count):
      handler.doRollover()
      # The assertion checks that there are at most new_backup_count files.
      assert len(os.listdir(handler.logdir)) <= (new_backup_count +
                                                 BACKUP_COUNT_EXEMPT_FILES)

  def test_DeleteMultipleInstancesPastBackupCount(self):
    """No more than backup count logs are kept across intances.

    Additionally, this test validates that the oldest get deleted.
    """
    new_backup_count = 3
    setattr(servo_logging, 'LOG_BACKUP_COUNT', new_backup_count)
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      port=self.port)
    first_ts = handler.ts
    for _ in range(new_backup_count):
      handler.doRollover()
      # The assertion checks that there are at most new_backup_count files.
      assert len(os.listdir(handler.logdir)) <= (new_backup_count +
                                                 BACKUP_COUNT_EXEMPT_FILES)
    # Creating a new instance changes the timestamp. This is to ensure that old
    # file deletion is not only done on the current instance's timestamp.
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      port=self.port)
    for _ in range(new_backup_count):
      handler.doRollover()
      # The assertion checks that there are at most new_backup_count files.
      assert len(os.listdir(handler.logdir)) <= (new_backup_count +
                                                 BACKUP_COUNT_EXEMPT_FILES)
    # After two new_backup_count rotations, the first timestamp should no longer
    # be around as it has been rotated out. Verify that.
    assert not any(first_ts in f for f in os.listdir(handler.logdir))

  def test_RotatePreviousInstance(self):
    """Creating a new instance rotates the old instances current log."""
    # Expand the sub-second component to generate different file names in this
    # test as the two handlers might be generated in the same millisecond.
    servo_logging.TS_MS_FORMAT = '%.7f'
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      port=self.port)
    self._installFH(handler)
    self.test_logger.info('Test content.')
    # Add a small delay between creating the instances to let the timestamps
    # be different.
    # Creating a new instance should force a rotation of the logfile.
    _ = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                port=self.port)
    assert not os.path.exists(handler.baseFilename)
    assert os.path.exists('%s.%s' % (handler.baseFilename,
                                     servo_logging.COMPRESSION_SUFFIX))

  def test_RotationMovesFilesAlong(self):
    """Rotation moves the same logfile's sequence number forward."""
    # Number of times this test will rotate out the log file after its first
    # compression.
    rotations = 3
    # The rotation starts at 2 as the first compression happens at index 1.
    start_rotation = 2
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      port=self.port)
    self._installFH(handler)
    self.test_logger.info('This is just some test content.')
    handler.doRollover()
    # At this point the compressed log-file should exist.
    rolled_fn = get_rolled_fn(handler.baseFilename, 1)
    assert os.path.exists(rolled_fn)
    md5sum = get_file_md5sum(rolled_fn)
    for i in range(start_rotation, start_rotation + rotations):
      handler.doRollover()
      rolled_fn = get_rolled_fn(handler.baseFilename, i)
      # Ensure that the file was rotated properly.
      assert os.path.exists(rolled_fn)
      # Ensure that the file is the same that started the rotation by validating
      # the checksum.
      assert md5sum == get_file_md5sum(rolled_fn)

  def test_CreateLogDirIfNotAvailable(self):
    """The output directory for a specific port is created on demand."""
    output_dir = servo_logging._buildLogdirName(self.logdir, self.port)
    assert not os.path.isdir(output_dir)
    _ = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                port=self.port)
    assert os.path.isdir(output_dir)

  def test_HandleExistingLogDir(self):
    """The output directory for a specific port already existing is fine."""
    output_dir = servo_logging._buildLogdirName(self.logdir, self.port)
    os.makedirs(output_dir)
    _ = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                port=self.port)
    assert os.path.isdir(output_dir)

if __name__ == '__main__':
  unittest.main()
