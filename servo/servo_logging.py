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
import sys
import tarfile
import time


# Format strings used for servod logging.
DEFAULT_FMT_STRING = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEBUG_FMT_STRING = ('%(asctime)s - %(name)s - %(levelname)s - '
                    '%(filename)s:%(lineno)d:%(funcName)s - %(message)s')

# Convenience map to have access to format string and level using a shorthand.
LOGLEVEL_MAP = {
    'critical': (logging.CRITICAL, DEFAULT_FMT_STRING),
    'error': (logging.ERROR, DEFAULT_FMT_STRING),
    'warning': (logging.WARNING, DEFAULT_FMT_STRING),
    'info': (logging.INFO, DEFAULT_FMT_STRING),
    'debug': (logging.DEBUG, DEBUG_FMT_STRING)
}

# Default loglevel used on servod for stdout logger.
DEFAULT_LOGLEVEL = 'info'

# Levels used to generate logs in servod in parallel.
# On initialization, a handler for each of these levels is created.
LOGLEVEL_FILES = ['debug', 'warning', 'info']

# Max log size for one log file. ~10 MB
MAX_LOG_BYTES_COMPRESSED = 1024 * 1024 * 10

# Tests have shown this to be roughly accurate for servod log compression.
SERVO_LOG_COMPRESSION_RATIO = 20

# This is used to calculate how big to let a file grow before compression.
MAX_LOG_BYTES = MAX_LOG_BYTES_COMPRESSED * SERVO_LOG_COMPRESSION_RATIO

# Max number of logs to keep around per port.
# Since logging is used for multiple concurrent logfiles (DEBUG, INFO, WARNING)
# this limit is set assuming that the output of INFO + WARNING will not be more
# than DEBUG.
# Going with the extreme assumption of 10 servo instances this means at
# most 10GB per port i.e. 100GB of logs if all log files are saturated.
LOG_BACKUP_COUNT = 512

# Filetype suffix used for compressed logs.
COMPRESSION_SUFFIX = 'tbz2'

# Each servo-port receives its own log directory. This is the prefix for those
# directory names.
LOG_DIR_PREFIX = 'servod'

# Each logfile starts with this prefix.
LOG_FILE_PREFIX = 'log'

# link name to the latest, open log file
LINK_PREFIX = 'latest'

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
  """Helper to generate the log directory for an instance at |port|.

  Args:
    logdir: path to directory where all of servod logging should reside
    port: port of the instance for the logger

  Returns:
    str, path for directory where servod logs for instance at |port| should go
  """
  return os.path.join(logdir, '%s_%s' % (LOG_DIR_PREFIX, str(port)))


def _generateTs():
  """Helper to generate a timestamp to tag per-instance logs.

  Returns:
    formatted timestamp of time when called
  """
  # pylint: disable=invalid-name
  # File is an extension to the standard library logger. Conform to their code
  # style.
  raw_ts = time.time()
  return (time.strftime(TS_FORMAT, time.gmtime(raw_ts)) +
          (TS_MS_FORMAT % (raw_ts % 1))[1:])


def _compress_old_files(logdir, logging_ts):
  """Helper to compress files that aren't using the current |logging_ts|.

  Files that aren't using |logging_ts| in their filename but are in the same
  port directory are presumed to be old and not in use, as only one instance
  can be running on a given port, and that instance (this) is using
  |logging_ts|. This closes and compresses those old logs.

  Args:
    logdir: str, path to servod instance log directory (e.g. /..../servod_9999/)
    logging_ts: timestamp used to tag current instance
  """
  for candidate_file in os.listdir(logdir):
    candidate_path = os.path.join(logdir, candidate_file)
    if os.path.islink(candidate_path):
      # No need to compress links, rather remove them, and let servod rebuild
      # them.
      os.remove(candidate_path)
    elif (logging_ts not in candidate_path and
          COMPRESSION_SUFFIX not in candidate_path):
      ServodRotatingFileHandler.compressFn(candidate_path)


def setup(logdir, port, debug_stdout=False):
  """Setup servod logging.

  This function handles setting up logging, whether it be normal basicConfig
  logging, or using logdir and file logging in servod.

  Args:
    logdir: str, log directory for all servod logs (*)
    port: port used for current instance
    debug_stdout: whether the stdout logs should be debug

  (*) if |logdir| is None, the system will not setup log handlers, but rather
  setup logging using basicConfig()
  """
  # pylint: disable=invalid-name
  # File is an extension to the standard library logger. Conform to their code
  # style.
  root_logger = logging.getLogger()
  # Let the root logger process every log message, while the different
  # handlers chose which ones to put out.
  root_logger.setLevel(logging.DEBUG)
  stdout_level = 'debug' if debug_stdout else DEFAULT_LOGLEVEL
  level, fmt = LOGLEVEL_MAP[stdout_level]
  # |log_dir| is None iff it's not in the cmdline. Otherwise it contains
  # a directory path to store the servod logs in.
  # Start file loggers for each output file.
  if not logdir:
    # In this case, servod requests that no file logging is done.
    logging.basicConfig(level=level, format=fmt)
  else:
    # File logging requires different handlers.
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.formatter = logging.Formatter(fmt=fmt)
    root_logger.addHandler(stdout_handler)
    instance_logdir = _buildLogdirName(logdir, port)
    logging_ts = _generateTs()
    if not os.path.isdir(instance_logdir):
      os.makedirs(instance_logdir)
    # Compress all currently open files with the old timestamps.
    # It's safe to remove this, as no 2 servod instances can be listening
    # on the same port. Therefore, the file currently 'alive' is not being
    # logged to anymore, and can be safely compressed.
    _compress_old_files(instance_logdir, logging_ts)
    for level in LOGLEVEL_FILES:
      fh_level, fh_fmt = LOGLEVEL_MAP[level]
      fh = ServodRotatingFileHandler(logdir=instance_logdir, ts=logging_ts,
                                     fmt=fh_fmt, level=fh_level)
      root_logger.addHandler(fh)


class ServodRotatingFileHandler(logging.handlers.RotatingFileHandler):
  """Extension to the default RotatingFileHandler.

  The two additions are:
    - rotated files are compressed
    - backup count is applied across the directory and not just the base
  See above for details.
  """

  def __init__(self, logdir, ts, fmt, level=logging.DEBUG):
    """Wrap original init by forcing one rotation on init.

    Args:
      logdir: str, path to log output directory
      ts: str, timestamp used to create logfile name for this instance
      fmt: str, output format to use
      level: loglevel to use
    """
    self.levelsuffix = logging.getLevelName(level)
    self._logger = logging.getLogger('%s.%s' %(type(self).__name__,
                                               self.levelsuffix))
    self.linkname = '%s.%s' % (LINK_PREFIX, self.levelsuffix)
    self.logdir = logdir
    filename = self._buildFilename(ts)
    logging.handlers.RotatingFileHandler.__init__(self, filename=filename,
                                                  backupCount=LOG_BACKUP_COUNT,
                                                  maxBytes=MAX_LOG_BYTES)
    self.updateConvenienceLink()
    # Level and format for ServodRotatingFileHandlers are set once at init
    # and then cannot be changed. Therefore, those methods are wrapped in a
    # noop.
    formatter = logging.Formatter(fmt=fmt)
    logging.handlers.RotatingFileHandler.setLevel(self, level)
    logging.handlers.RotatingFileHandler.setFormatter(self, formatter)

  def setLevel(self, level):
    """Noop to avoid setLevel being triggered."""
    self._logger.warning('setLevel is not supported on %s. Please consider '
                         'changing the code here.', type(self).__name__)

  def setFormatter(self, fmt):
    """Noop to avoid setFormatter being triggered."""
    self._logger.warning('setFormatter is not supported on %s. Please consider '
                         'changing the code here.', type(self).__name__)

  def updateConvenienceLink(self):
    # pylint: disable=invalid-name
    # File is an extension to the standard library logger. Conform to their code
    # style.
    """Generate a symbolic link to the latest file."""
    linkfile = os.path.join(self.logdir, self.linkname)
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
    return os.path.join(self.logdir, '%s.%s.%s' % (LOG_FILE_PREFIX, ts,
                                                   self.levelsuffix))

  @staticmethod
  def compressFn(path):
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
      ServodRotatingFileHandler.compressFn(rolled_fn)
      # Servod backup counts are meant across invocations on the same port,
      # therefore this needs to count all files in the logdir and make sure
      # that the backup count does not grow too large.
      files = [os.path.join(self.logdir, fp) for fp in os.listdir(self.logdir)
               if fp.endswith(COMPRESSION_SUFFIX)]
      files.sort(reverse=True)
      files_to_remove = files[self.backupCount:]
      for fp in files_to_remove:
        os.remove(fp)
