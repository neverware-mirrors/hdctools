# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servodtool manager."""

import argparse
import logging
import sys

import tools


class ServodToolError(Exception):
  """Servodtool error class."""
  pass


def setup_logging():
  """Setup logging for the command line tool."""
  root_logger = logging.getLogger()
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.INFO)
  root_logger.setLevel(logging.DEBUG)
  root_logger.addHandler(stdout_handler)


# TODO(coconutruben): phase this out. For now, users are still expecting this
# tool, and some autotest code might still rely on this. Once all the
# dependencies are eliminated for servodtool, then remove this.
def servodutil(cmdline=sys.argv[1:]):
  """Legacy, to keep the old command-line tool in place."""
  setup_logging()
  parser = argparse.ArgumentParser()
  instance_tool = tools.instance.Instance()
  instance_tool.add_args(parser)
  args = parser.parse_args(cmdline)
  instance_tool.run(args)


# pylint: disable=dangerous-default-value
def main(cmdline=sys.argv[1:]):
  """Entry function for cmdline servodtool utility."""
  # pylint: disable=protected-access
  setup_logging()
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(dest='tool')
  # Make a dictionary of tool names and the actual tool.
  tool_dict = {}
  for tool_cls in tools.REGISTERED_TOOLS:
    t = tool_cls()
    tool_dict[t.name] = t
  for tname in tool_dict:
    t = tool_dict[tname]
    tparser = subparsers.add_parser(tname, help=t.help)
    tool_dict[tname].add_args(tparser)
  args = parser.parse_args(cmdline)
  tool_dict[args.tool].run(args)


if __name__ == '__main__':
  main()
