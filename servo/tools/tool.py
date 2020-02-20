# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Base tool class implementing the servodtool interface."""


import logging


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

  def run(self, args):
    """Execute the tool after parsing."""
    raise NotImplementedError('Tools need to provide an implementation.')
