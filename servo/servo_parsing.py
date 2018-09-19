# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common code for servo_parsing operation support"""

import argparse
import os
import sys
import textwrap

if os.getuid():
  DEFAULT_RC_FILE = '/home/%s/.servodrc' % os.getenv('USER', '')
else:
  DEFAULT_RC_FILE = '/home/%s/.servodrc' % os.getenv('SUDO_USER', '')


class ServodParserHelpFormatter(argparse.RawDescriptionHelpFormatter,
                                argparse.ArgumentDefaultsHelpFormatter):
  """Servod help formatter.

  Combines ability for raw description printing (needed to have control over
  how to print examples) and default argument printing, printing the default
  which each argument.
  """
  pass


class ServodParserError(Exception):
  """Error class for Servod parsing errors."""
  pass


class _BaseServodParser(argparse.ArgumentParser):
  """Extension to ArgumentParser that allows for examples in the description.

  _BaseServodParser allows for a list of example tuples, where
    element[0]: is the cmdline invocation
    element[1]: is a comment to explain what the invocation does.

  For example (loosely based on servod.)
  ('-b board', 'Start servod with the configuation for board |board|')
  would print the following help message:
  ...

  Examples:
    > servod -b board
        Start servod with the configuration for board |board|

  Optional Arguments...

  see servod, or dut_control for more examples.
  """

  def __init__(self, description='', examples=None, *args, **kwargs):
    """Initialize _BaseServodParser by setting description and formatter.

    Args:
      args: positional arguments forwarded to ArgumentParser
      description: description of the program
      examples: list of tuples where the first element is the cmdline example,
                and the second element is a comment explaining the example.
                %(prog)s will be prepended to each example if it does not
                start with %(prog)s.
      kwargs: keyword arguments forwarded to ArgumentParser
    """
    # Generate description.
    description_lines = textwrap.wrap(description)
    # Setting it into the kwargs here ensures that we overwrite an potentially
    # passed in and undesired formatter class.
    kwargs['formatter_class'] = ServodParserHelpFormatter
    if examples:
      # Extra newline to separate description from examples.
      description_lines.append('\n')
      description_lines.append('Examples:')
      for example, comment in examples:
        if not example.startswith('%(prog)s'):
          example = '%(prog)s ' + example
        example_lines = ['  > ' + example]
        example_lines.extend(textwrap.wrap(comment))
        description_lines.append('\n\t'.join(example_lines))
    description = '\n'.join(description_lines)
    kwargs['description'] = description
    super(_BaseServodParser, self).__init__(*args, **kwargs)


class BaseServodParser(_BaseServodParser):
  """BaseServodParser handling common arguments in the servod cmdline tools."""

  def __init__(self, *args, **kwargs):
    """Initialize by adding common arguments.

    Adds:
    - host/port arguments to find/initialize a servod instance
    - debug argument to toggle debug message printing
    - name/rcfile arguments to handle servodrc configurations

    Args:
      args: positional arguments forwarded to _BaseServodParser
      kwargs: keyword arguments forwarded to _BaseServodParser
    """
    super(BaseServodParser, self).__init__(*args, **kwargs)
    self.add_argument('-d', '--debug', action='store_true', default=False,
                      help='enable debug messages')
    self.add_argument('--host', default='localhost', type=str,
                      help='hostname of the servod server.')
    self.add_argument('-p', '--port', default=None, type=int,
                      help='port of the servod server.')


def add_servo_parsing_rc_options(parser):
  """Add common options descriptors to the parser object

  Both servod and dut-control accept command line options for configuring
  servo_parsing operation. This function configures the command line parser
  object to accept those options.
  """
  parser.add_argument('--rcfile', type=str, default=DEFAULT_RC_FILE,
                      help='servo description file for multi-servo operation.')
  parser.add_argument('-n', '--name', type=str,
                      help='symbolic name of the servo board, '
                      'used as a config shortcut, could also be supplied '
                      'through environment variable SERVOD_NAME')


def parse_rc(logger, rc_file):
  """Parse servodrc configuration file

  The format of the configuration file is described above in comments to
  DEFAULT_RC_FILE. I the file is not found or is mis-formatted, a warning is
  printed but the program tries to continue.

  Args:
    logger: a logging instance used by this servod driver
    rc_file: a string, name of the file storing the configuration

  Returns:
    a dictionary, where keys are symbolic servo names, and values are
    dictionaries representing servo parameters read from the config file,
    keyed by strings 'sn' (for serial number), 'port', 'board', and 'model'.
  """

  rcd = {}  # Dictionary representing the rc file contents.
  if os.path.isfile(rc_file):
    for rc_line in open(rc_file, 'r').readlines():
      line = rc_line.split('#')[0].strip()
      if not line:
        continue
      elts = [x.strip() for x in line.split(',')]
      name = elts[0]
      if not name or len(elts) < 2 or [x for x in elts if ' ' in x]:
        logger.info('ignoring rc line "%s"', rc_line.rstrip())
        continue
      rcd[name] = {'sn': elts[1], 'port': None, 'board': None, 'model': None}
      if (len(elts) > 2):
        rcd[name]['port'] = int(elts[2])
        if len(elts) > 3:
          rcd[name]['board'] = elts[3]
          if len(elts) > 4:
            rcd[name]['model'] = elts[4]
            if len(elts) > 5:
              logger.info('discarding %s for for %s', ' '.join(elts[5:]), name)
  return rcd


def get_env_options(logger, options):
  """Look for non-defined options in the environment

  SERVOD_PORT and SERVOD_NAME environment variables can be used if --port
  and --name command line switches are not set. Set the options values as
  necessary.

  Args:
    logger: a logging instance used by this servod driver
    options: the options object returned by opt_parse
  """
  if not options.port:
    env_port = os.getenv('SERVOD_PORT')
    if env_port:
      try:
        options.port = int(env_port)
      except ValueError:
        logger.warning('Ignoring environment port definition "%s"', env_port)
  if not options.name:
    options.name = os.getenv('SERVOD_NAME')
