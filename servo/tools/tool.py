# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Base tool class implementing the servodtool interface."""


import logging
import sys


class ToolError(Exception):
  """General tool error class."""
  pass


class Tool(object):
  """Base class implementing the tool interface.

  A tool is a tool invoked through servodtool [tool] [args...] and provides
  aditional functionality to servod outside of the instance. Think instance
  management, log parsing, etc.
  """

  def __init__(self):
    """Setup scratch to use."""
    self._logger = logging.getLogger(type(self).__name__)
    # Set the lower case name for the tool so that the parser can know
    # what the tool is.
    self.name = type(self).__name__.lower()

  @property
  def help(self):
    raise NotImplementedError('A tool needs to provide a help script.')

  def add_args(self, tool_parser):
    """Add the arguments needed for this tool."""
    raise NotImplementedError('Tools need to provide their args.')

  def error(self, msg, *args):
    # pylint: disable=invalid-name
    """Log error and exit.

    Args:
      msg: message to log
      *args: args to pass to logging module
    """
    self._logger.info(msg, *args)
    sys.exit(1)

  def run(self, args):
    """Execute the tool after parsing.

    Args:
      args: argparse.parse_arguments() returned namespace to execute a command

    The default invocation is that a tool, for each sub-command, implements
    a method that's just the commadn with '-' replaced wiht '_'.
    The tool is of course free to overwrite run() to have a custom invocation
    logic.
    """
    cmd = args.command.replace('-', '_')
    getattr(self, cmd)(args)
