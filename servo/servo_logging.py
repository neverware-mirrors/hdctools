# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Module for logging on servod.

The logging extension here is meant to support easier debugging and make sure
that no information is lost, and finding the right information is simple.
The basic structure is that inside a directory (by default /var/log/ there
are servod log directories, one per port. As there can only be at most one
instance per port, this removes the need to coordinate file writing and
rotation across instances.
Inside that directory, the logs are compressed after rotation, except for the
log file currently in use.
Each log file has the following naming convention.
log.YYYY-MM-DD@HH:MM:SS.MS[.x.tbz2]
(prefix).(invocation date & time (UTC))[seq num][compressed type if rotated]
e.g. log.2019-07-01@21:21:06.9582.1.tbz2
When a new instance is started on the same port, the old open log is closed
and rotated, and a new log file with a new timestamp is started.
So all files for one invocation share the same timestamp in the filename,
and can be read sequentially by using the sequence numbers.
All instances on the same port are in the same directory.
"""

import logging
import logging.handlers
import os
import tarfile
import time

# Max log size for one log file. ~10 MB
MAX_LOG_BYTES_COMPRESSED = 1024 * 1024 * 10

# Tests have shown this to be roughly accurate for servod log compression.
SERVO_LOG_COMPRESSION_RATIO = 20

# This is used to calculate how big to let a file grow before compression.
MAX_LOG_BYTES = MAX_LOG_BYTES_COMPRESSED * SERVO_LOG_COMPRESSION_RATIO

# Max number of logs to keep around per port.
# Going with the extreme assumption of 10 servo instances this means at
# most 10GB per port i.e. 100GB of logs if all log files are saturated.
LOG_BACKUP_COUNT = 1024

# Filetype suffix used for compressed logs.
COMPRESSION_SUFFIX = 'tbz2'

# Each servo-port receives its own log directory. This is the prefix for those
# directory names.
LOG_DIR_PREFIX = 'servod'

# Each logfile starts with this prefix.
LOG_FILE_PREFIX = 'log'

# link name to the latest, open log file
LINK_NAME = 'latest'

# The timestamp that identifies the instance is cached in this file.
TS_FILE = 'ts'

# Format string for the timestamps used instance differentiation.
TS_FORMAT = '%Y-%m-%d@%H:%M:%S'

# The format string for the millisecond component in the ts.
TS_MS_FORMAT = '%.3f'


def _buildLogdirName(logdir, port):
  # pylint: disable=invalid-name
  # File is an extension to the standard library logger. Conform to their code
  # style.
  """Helper to generate the log directory for an instance at |port|."""
  return os.path.join(logdir, '%s_%s' % (LOG_DIR_PREFIX, str(port)))


class ServodRotatingFileHandler(logging.handlers.RotatingFileHandler):
  """Extension to the default RotatingFileHandler.

  The two additions are:
    - rotated files are compressed
    - backup count is applied across the directory and not just the base
  See above for details.
  """

  def __init__(self, logdir, port):
    """Wrap original init by forcing one rotation on init."""
    self.logdir = _buildLogdirName(logdir, port)
    if os.path.isdir(self.logdir):
      old_ts, ts = self.setTs()
      previous_instance_fn = self._buildFilename(old_ts)
      if os.path.exists(previous_instance_fn):
        # It's safe to remove this, as no 2 servod instances can be listening
        # on the same port. Therefore, the file currently 'alive' is not being
        # logged to anymore, and can be safely compressed.
        self.compressFn(previous_instance_fn)
    else:
      os.makedirs(self.logdir)
      _, ts = self.setTs()
    filename = self._buildFilename(ts)
    self.ts = ts
    logging.handlers.RotatingFileHandler.__init__(self, filename=filename,
                                                  backupCount=LOG_BACKUP_COUNT,
                                                  maxBytes=MAX_LOG_BYTES)
    self.updateConvenienceLink()

  def updateConvenienceLink(self):
    # pylint: disable=invalid-name
    # File is an extension to the standard library logger. Conform to their code
    # style.
    """Generate a symbolic link to the latest file."""
    linkfile = os.path.join(self.logdir, LINK_NAME)
    if os.path.lexists(linkfile):
      os.remove(linkfile)
    os.symlink(self.baseFilename, linkfile)

  def _buildFilename(self, ts):
    # pylint: disable=invalid-name
    # File is an extension to the standard library logger. Conform to their code
    # style.
    """Helper to build the active log file's filename.

    Args:
      ts: timestamp string

    Returns:
      Full path of the logfile for the given timestamp.
    """
    return os.path.join(self.logdir, '%s.%s' % (LOG_FILE_PREFIX, ts))

  def setTs(self):
    # pylint: disable=invalid-name
    # File is an extension to the standard library logger. Conform to their code
    # style.
    """Generate a timestamp and cache it in |logdir|.

    Returns:
      (old_ts, ts) where old_ts is the old cache entry if any, and ts is the
                   newly generated stamp.
    """
    raw_ts = time.time()
    ts = '%s%s' % (time.strftime(TS_FORMAT, time.gmtime(raw_ts)),
                   (TS_MS_FORMAT % (raw_ts % 1))[1:])
    ts_path = os.path.join(self.logdir, TS_FILE)
    if os.path.exists(ts_path):
      with open(ts_path, 'r') as f:
        old_ts = f.read().strip()
    else:
      old_ts = None
    with open(ts_path, 'w') as f:
      f.write(ts)
    return (old_ts, ts)

  def compressFn(self, path):
    # pylint: disable=invalid-name
    # File is an extension to the standard library logger. Conform to their code
    # style.
    """Compress file at |path|.

    Args:
      path: path to file to compress.
    """
    compressed_path = '%s.%s' % (path, COMPRESSION_SUFFIX)
    with tarfile.open(compressed_path, 'w:bz2') as tar:
      tar.add(path, recursive=False)
    # This file has been compressed and can be safely deleted now.
    os.remove(path)

  def doRollover(self):
    """Extend stock doRollover to support compression.

    In addition to regular filename rotation (on the compressed logs) this also
    ensures that the backup count does not grow beyond the backup count across
    the |logdir| and not just the baseFilename.
    """
    logging.handlers.RotatingFileHandler.doRollover(self)
    self.updateConvenienceLink()
    rolled_fn = '%s.%d' % (self.baseFilename, 1)
    if os.path.exists(rolled_fn):
      # If a rollover actually occured, we need to compress and rotate all
      # old compressed files.
      for i in range(self.backupCount - 1, 0, -1):
        src = '%s.%d.%s' % (self.baseFilename, i, COMPRESSION_SUFFIX)
        dst = '%s.%d.%s' % (self.baseFilename, i + 1, COMPRESSION_SUFFIX)
        if os.path.exists(src):
          os.rename(src, dst)
      # Compress the latest rotated doc.
      self.compressFn(rolled_fn)
      # Servod backup counts are meant across invocations on the same port,
      # therefore this needs to count all files in the logdir and make sure
      # that the backup count does not grow too large.
      files = [os.path.join(self.logdir, fp) for fp in os.listdir(self.logdir)
               if fp.endswith(COMPRESSION_SUFFIX)]
      files.sort(reverse=True)
      files_to_remove = files[self.backupCount:]
      for fp in files_to_remove:
        os.remove(fp)
