# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servod's logging handler works as intended."""

import copy
import hashlib
import logging
import os
import shutil
import tempfile
import unittest

import servo_logging

# There is 1 file that are exempt from the backup count.
# - the 'latest' symbolic link
# - the open file that isn't a backup
BACKUP_COUNT_EXEMPT_FILES = 2


def get_file_md5sum(path):
  """Return the md5 checksum of the file at |path|."""
  with open(path, 'rb') as f:
    return hashlib.md5(f.read()).hexdigest()


def get_rolled_fn(logfile, rotations):
  """Helper to get filename of |logfile| after |rotations| log rotations."""
  return '%s.%d' % (logfile, rotations)


class TestServodRotatingFileHandler(unittest.TestCase):

  # These are module wide attributs to cache and restore after tests
  # in case the tests wish to modify them.
  MODULE_ATTRS = ['MAX_LOG_BYTES',  # Max bytes a log file can grow to.
                  'LOG_BACKUP_COUNT',  # Number of rotated logfiles to keep.
                  'UNCOMPRESSED_BACKUP_COUNT',  #  Uncompressed logfiles kept.
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
    self.loglevel = logging.DEBUG
    self.fmt = ''
    self.ts = servo_logging._generateTs()
    self.test_logger = logging.getLogger('Test')
    self.test_logger.setLevel(logging.DEBUG)
    self.test_logger.propagate = False
    self.module_defaults = {}
    # Cache the module wide attributs to restore them after each test again.
    for attr in self.MODULE_ATTRS:
      self.module_defaults[attr] = getattr(servo_logging, attr)
    # Expand the sub-second component to generate different file names in this
    # test as the two handlers might be generated in the same millisecond.
    setattr(servo_logging, 'TS_MS_FORMAT', '%.7f')

  def tearDown(self):
    """Delete logging directory, remove handlers,restore module data."""
    shutil.rmtree(self.logdir)
    unittest.TestCase.tearDown(self)
    self.test_logger.handlers = []
    # Restore cached module attributes.
    for attr, val in self.module_defaults.iteritems():
      setattr(servo_logging, attr, val)

  def test_LoggerLogsToFile(self):
    """Basic sanity that content is being output to the file."""
    test_str = 'This is a test string to make sure there is logging.'
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      ts=self.ts,
                                                      fmt=self.fmt,
                                                      level=self.loglevel)
    self.test_logger.addHandler(handler)
    self.test_logger.info(test_str)
    with open(handler.baseFilename, 'r') as log:
      assert log.read().strip() == test_str

  def test_RotationOccursWhenFileGrowsTooLarge(self):
    """Growing log-file beyond limit causes a rotation."""
    test_max_log_bytes = 40
    setattr(servo_logging, 'MAX_LOG_BYTES', test_max_log_bytes)
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      ts=self.ts,
                                                      fmt=self.fmt,
                                                      level=self.loglevel)
    self.test_logger.addHandler(handler)
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
    # Set the backup count to only be 3 compressed for this test.
    new_backup_count = servo_logging.UNCOMPRESSED_BACKUP_COUNT + 3
    setattr(servo_logging, 'LOG_BACKUP_COUNT', new_backup_count)
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      ts=self.ts,
                                                      fmt=self.fmt,
                                                      level=self.loglevel)
    for _ in range(2 * new_backup_count):
      handler.doRollover()
      # The assertion checks that there are at most new_backup_count files.
      assert len(os.listdir(handler.logdir)) <= (new_backup_count +
                                                 BACKUP_COUNT_EXEMPT_FILES)

  def test_DeleteMultipleInstancesPastBackupCount(self):
    """No more than backup count logs are kept across intances.

    Additionally, this test validates that the oldest get deleted.
    """
    new_backup_count = servo_logging.UNCOMPRESSED_BACKUP_COUNT + 3
    setattr(servo_logging, 'LOG_BACKUP_COUNT', new_backup_count)
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      ts=self.ts,
                                                      fmt=self.fmt,
                                                      level=self.loglevel)
    for _ in range(new_backup_count):
      handler.doRollover()
      # The assertion checks that there are at most new_backup_count files.
      assert len(os.listdir(handler.logdir)) <= (new_backup_count +
                                                 BACKUP_COUNT_EXEMPT_FILES)
    # Change the timestamp and create a new instance. Rotate out all old files.
    new_ts = servo_logging._generateTs()
    servo_logging._compressOldFiles(logdir=self.logdir)
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      ts=new_ts,
                                                      fmt=self.fmt,
                                                      level=self.loglevel)
    for _ in range(new_backup_count):
      handler.doRollover()
      # The assertion checks that there are at most new_backup_count files.
      assert len(os.listdir(handler.logdir)) <= (new_backup_count +
                                                 BACKUP_COUNT_EXEMPT_FILES)
    # After two new_backup_count rotations, the first timestamp should no longer
    # be around as it has been rotated out. Verify that.
    assert not any(self.ts in f for f in os.listdir(handler.logdir))

  def test_SortLogsOneInstance(self):
    """Verify log-sorting is per instance in order of newest first."""
    loglevel = logging.getLevelName(self.loglevel)
    # Generate fake logfile names.
    instance_tag = '%s.%s' % (servo_logging.LOG_FILE_PREFIX,
                              servo_logging._generateTs())
    # This mimicks the active, open logfile.
    logfiles = ['%s.%s' % (instance_tag, loglevel)]
    for i in range(5):
      logfiles.append('%s.%s.%d' % (instance_tag, loglevel, i))
    sorted_logfiles = copy.copy(logfiles)
    # Do not use randomization but rather swap each element pair to
    # created a predictable unsorted system.
    for idx in range(0, len(logfiles), 2):
      placeholder = logfiles[idx]
      logfiles[idx] = logfiles[idx+1]
      logfiles[idx+1] = placeholder
    allegedly_sorted_logfiles = servo_logging._sortLogs(logfiles, loglevel)
    assert allegedly_sorted_logfiles == sorted_logfiles

  def test_SortLogsAcrossInstances(self):
    """Verify log-sorting is across instances newest first."""
    loglevel = logging.getLevelName(self.loglevel)
    # Generate fake logfile names.
    stale_tag = '%s.%s' % (servo_logging.LOG_FILE_PREFIX,
                           servo_logging._generateTs())
    fresh_tag = '%s.%s' % (servo_logging.LOG_FILE_PREFIX,
                           servo_logging._generateTs())
    # This mimicks the active, open logfiles.
    logfiles = ['%s.%s' % (fresh_tag, loglevel)]
    logfiles.append('%s.%s' % (stale_tag, loglevel))
    for i in range(1, 6):
      # Adding them both at the same time here ensures a predicable way of
      # having the list be unsorted.
      logfiles.append('%s.%s.%d' % (fresh_tag, loglevel, i))
      logfiles.append('%s.%s.%d' % (stale_tag, loglevel, i))
    unsorted_logfiles = copy.copy(logfiles)
    # The fresh tags are every odd element in the list.
    sorted_logfiles = unsorted_logfiles[0::2] + unsorted_logfiles[1::2]
    # Do not use randomization but rather swap each element pair to
    # created a predictable unsorted system.
    for idx in range(0, len(logfiles), 2):
      placeholder = logfiles[idx]
      logfiles[idx] = logfiles[idx+1]
      logfiles[idx+1] = placeholder
    # The expectation here is that at first all fresh_tags show up, followed
    # by all state_tags, and within those, there is ordering.
    allegedly_sorted_logfiles = servo_logging._sortLogs(logfiles, loglevel)
    assert allegedly_sorted_logfiles == sorted_logfiles

  def test_CompressOldFiles(self):
    """At most |UNCOMPRESSED_BACKUP_COUNT| around after old file compression."""
    self.ts = servo_logging._generateTs()
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      ts=self.ts,
                                                      fmt=self.fmt,
                                                      level=self.loglevel)
    self.test_logger.addHandler(handler)
    self.test_logger.info('Test content.')
    for _ in range(servo_logging.UNCOMPRESSED_BACKUP_COUNT):
      handler.doRollover()
    # At this point the maximum number of uncompressed files should exist.
    new_ts = servo_logging._generateTs()
    handler2 = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                       ts=new_ts,
                                                       fmt=self.fmt,
                                                       level=self.loglevel)
    for _ in range(servo_logging.UNCOMPRESSED_BACKUP_COUNT):
      handler2.doRollover()
    # At this point both handlers have created the maximum number of
    # uncompressed logs. Since they both use the same suffix, compression
    # should compress all the ones from the first handler.
    pre_purge_filecount = len([f for f in os.listdir(self.logdir) if
                               servo_logging.COMPRESSION_SUFFIX not in f])
    servo_logging._compressOldFiles(logdir=self.logdir)
    post_purge_filecount = len([f for f in os.listdir(self.logdir) if
                                servo_logging.COMPRESSION_SUFFIX not in f])
    assert pre_purge_filecount == post_purge_filecount
    assert not os.path.exists(handler.baseFilename)
    cls = servo_logging.ServodRotatingFileHandler
    handler_compressed_fn = cls.getCompressedPathname(handler.baseFilename)
    assert os.path.exists(handler_compressed_fn)

  def test_CompressOldFilesTwoLoglevels(self):
    """At most |UNCOMPRESSED_BACKUP_COUNT| are kept per loglevel."""
    self.ts = servo_logging._generateTs()
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      ts=self.ts,
                                                      fmt=self.fmt,
                                                      level=self.loglevel)
    self.test_logger.addHandler(handler)
    self.test_logger.info('Test content.')
    for _ in range(servo_logging.UNCOMPRESSED_BACKUP_COUNT):
      handler.doRollover()
    # At this point the maximum number of uncompressed files should exist.
    new_ts = servo_logging._generateTs()
    handler2 = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                       ts=new_ts,
                                                       fmt=self.fmt,
                                                       level=logging.INFO)
    for _ in range(servo_logging.UNCOMPRESSED_BACKUP_COUNT):
      handler2.doRollover()
    # At this point both handlers have created the maximum number of
    # uncompressed logs. Since they both use different loglevels
    # no files should be purged or compressed.
    pre_purge_filecount = len([f for f in os.listdir(self.logdir) if
                               servo_logging.COMPRESSION_SUFFIX not in f])
    servo_logging._compressOldFiles(logdir=self.logdir)
    post_purge_filecount = len([f for f in os.listdir(self.logdir) if
                                servo_logging.COMPRESSION_SUFFIX not in f])
    assert pre_purge_filecount == post_purge_filecount
    # Ensure the file hasn't been compressed.
    assert os.path.exists(handler.baseFilename)
    cls = servo_logging.ServodRotatingFileHandler
    handler_compressed_fn = cls.getCompressedPathname(handler.baseFilename)
    assert not os.path.exists(handler_compressed_fn)

  def test_RotationMovesFilesAlong(self):
    """Rotation moves the same logfile's sequence number forward."""
    # Number of times this test will rotate out the log file after its first
    # compression.
    rotations = 3
    # The rotation starts at 2 as the first compression happens at index 1.
    start_rotation = 2
    handler = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                      ts=self.ts,
                                                      fmt=self.fmt,
                                                      level=self.loglevel)
    self.test_logger.addHandler(handler)
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

  def test_HandleExistingLogDir(self):
    """The output directory for a specific port already existing is fine."""
    output_dir = servo_logging._buildLogdirName(self.logdir, 9998)
    os.makedirs(output_dir)
    _ = servo_logging.ServodRotatingFileHandler(logdir=self.logdir,
                                                ts=self.ts,
                                                fmt=self.fmt,
                                                level=self.loglevel)
    assert os.path.isdir(output_dir)

if __name__ == '__main__':
  unittest.main()
