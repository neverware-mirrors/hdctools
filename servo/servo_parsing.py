# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common code for servo parsing support."""

import argparse
import logging
import os
import textwrap

import client
import servo_logging
import servodutil


# A brief overview of the classes found here, and their abilities.
# Indentation indicates inheritance.
#
# _BaseServodParser: ArgumentParser with pretty-formatting for example list
#
#   BaseServodParser: adds common args: port, host, and debug
#
#   ServodRCParser: adds -name/-rcfile & overwrites parsing logic so that
#                   rc parsing & configuration is handled internally
#                   i.e. the program does not need to know anything about
#                   the servodrc system
#
#     ServodClientParser: parser intended for servod clients (e.g. dut-control)
#                         - has all the BaseServodParser and ServodRCParser args
#                         - has the native rc configuration handling
#                         - adds a serialname argument that gets mapped to a
#                           port using ServoScratch


# This text file holds servod configuration parameters. This is especially
# handy for multi servo operation.
#
# The file format is pretty loose:
#  - text starting with # is ignored til the end of the line
#  - empty lines are ignored
#  - configuration lines consist of up to 5 comma separated fields (all
#    but the first field optional):
#        servo-name, serial-number, port-number, board-name, board-model
#
#    where
#     . servo-name - a user defined symbolic name, just a reference
#                    to a certain servo board
#     . serial-number - serial number of the servo board this line pertains to
#     . port-number - desired port number for servod for this board, can be
#                     overridden by the command line switch --port or
#                     environment variable setting SERVOD_PORT
#                     NOTE: this is no longer in use, and will be ignored.
#     . board-name - board configuration file to use, can be
#                    overridden by the command line switch --board
#     . model-name - model override to use, if applicable.
#                    overridden by command line --model
#
# Example lines in the rc-file:
# nocturne_micro, SNCQ00098, , nocturne # This is a nocturne without model
# octopus_micro, SNCQ00098, , octopus, npcx # This an octopus that defines model
#
# As you can see, the port part is left out for now. This will be phased out
# giving users time to adjust their rc files.
#
# Since the same parameters could be defined using different means, there is a
# hierarchy of definitions (left being the highest priority):
#   command line <- environment definition <- rc config file


if os.getuid():
  DEFAULT_RC_FILE = '/home/%s/.servodrc' % os.getenv('USER', '')
else:
  DEFAULT_RC_FILE = '/home/%s/.servodrc' % os.getenv('SUDO_USER', '')


PORT_ENV_VAR = 'SERVOD_PORT'
NAME_ENV_VAR = 'SERVOD_NAME'


ARG_BY_USER_MARKER = 'supplied_by_user'


def ArgMarkedAsUserSupplied(namespace, arg_name):
  """Query whether an argument that uses StoreAndMarkAction is user supplied."""
  marker_name = '%s_%s' % (arg_name, ARG_BY_USER_MARKER)
  return hasattr(namespace, marker_name)

# pylint: disable=protected-access
# Need to expand the StoreAction of the parser.
class StoreAndMarkAction(argparse._StoreAction):
  """Helper to mark arguments whether they were supplied by the user.

  If an argument is supplied by the user instead of using defaults or RC,
  add another option with the name |arg|_supplied_by_user.
  """

  def __call__(self, parser, namespace, values, option_string=None):
    """Extend default __call__ implementation."""
    # This sets the |values| to |self.dest|.
    super(StoreAndMarkAction, self).__call__(parser=parser, namespace=namespace,
                                             values=values,
                                             option_string=option_string)
    marker_name = '%s_%s' % (self.dest, ARG_BY_USER_MARKER)
    setattr(namespace, marker_name, True)


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

  def __init__(self, description='', examples=None, **kwargs):
    """Initialize _BaseServodParser by setting description and formatter.

    Args:
      description: description of the program
      examples: list of tuples where the first element is the cmdline example,
                and the second element is a comment explaining the example.
                %(prog)s will be prepended to each example if it does not
                start with %(prog)s.
      **kwargs: keyword arguments forwarded to ArgumentParser
    """
    # Initialize logging up here first to ensure log messages from parsing
    # can go through.
    loglevel, fmt = servo_logging.LOGLEVEL_MAP[servo_logging.DEFAULT_LOGLEVEL]
    logging.basicConfig(loglevel=loglevel, format=fmt)
    self._logger = logging.getLogger(type(self).__name__)
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
    super(_BaseServodParser, self).__init__(**kwargs)


class BaseServodParser(_BaseServodParser):
  """BaseServodParser handling common arguments in the servod cmdline tools."""

  def __init__(self, add_port=True, **kwargs):
    """Initialize by adding common arguments.

    Adds:
    - host/port arguments to find/initialize a servod instance
    - debug argument to toggle debug message printing

    Args:
      add_port: bool, whether to add --port to the parser. A caller might want
                to add port themselves either to rename it (servod-port),
                or to create mutual exclusion with serialname and name (clients)
      **kwargs: keyword arguments forwarded to _BaseServodParser
    """
    super(BaseServodParser, self).__init__(**kwargs)
    self.add_argument('-d', '--debug', action='store_true', default=False,
                      help='enable debug messages')
    self.add_argument('--host', default='localhost', type=str,
                      help='hostname of the servod server.')
    if add_port:
      BaseServodParser.AddRCEnabledPortArg(self)

  @staticmethod
  def AddRCEnabledPortArg(parser, port_flags=['-p', '--port']):
    """Add the port to the argparser.

    Set the default to environment variable ENV_PORT_NAME if defined

    Note: while this helper does allow for arbitrary flags for the port
    variable, the destination is still set to 'port'. It's on the caller to
    ensure that there is no conflict.

    Args:
      parser: parser or group to add argument to
      port_flags: optional, list, if the flags for the port should be different
                  than the default ones.
    """
    # pylint: disable=dangerous-default-value
    # Having the default flags here simplifies the code logic.
    default = os.environ.get(PORT_ENV_VAR, client.DEFAULT_PORT)
    parser.add_argument(*port_flags, default=default, type=int, dest='port',
                        action=StoreAndMarkAction,
                        help='port of the servod server. Can also be supplied '
                        'through environment variable ' + PORT_ENV_VAR)


class ServodRCParser(_BaseServodParser):
  """Base class to build Servod parsers to natively handle servorc.

  This class overwrites parse_args & parse_known_args to:
  - handle NAME_ENV_VAR environment variable
  - parse & substitute in the servorc file on matches
  """

  def __init__(self, **kwargs):
    super(ServodRCParser, self).__init__(**kwargs)
    self.add_argument('--rcfile', type=str, default=DEFAULT_RC_FILE,
                      help='servo description file for multi-servo operation.')
    # name and serialname are both ways to ID a servo device
    self._id_group = self.add_mutually_exclusive_group()
    self._id_group.add_argument('-s', '--serialname', default=None, type=str,
                                help='device serialname stored in eeprom.')
    ServodRCParser.AddRCEnabledNameArg(self._id_group)

  @staticmethod
  def AddRCEnabledNameArg(parser, name_flags=['-n', '--name']):
    """Add the name to the argparser.

    Set the default to environment variable ENV_VAR_NAME if defined

    Note: while this helper does allow for arbitrary flags for the name
    variable, the destination is still set to 'name'. It's on the caller to
    ensure that there is no conflict.

    Args:
      parser: parser or group to add argument to
      name_flags: optional, list, if the flags for the name should be different
                  than the default ones.
    """
    # pylint: disable=dangerous-default-value
    # Having the default flags here simplifies the code logic.
    default = os.environ.get(NAME_ENV_VAR, '')
    parser.add_argument(*name_flags, default=default, type=str, dest='name',
                        help='symbolic name of the servo board, '
                        'used as a config shortcut, could also be supplied '
                        'through environment variable ' + NAME_ENV_VAR)

  @staticmethod
  def PostProcessRCElements(options, rcpath=None, logger=logging):
    """Handle 'name' in |options| by substituting it with the intended config.

    This replaces the name option in the options with the intended serialname
    for that name if one can be found. If a board file is also specified in the
    rc file it appends that to the options too, which can be ignored if not
    needed.

    Note: this function changes the content of options.

    Args:
      options: argparse Namespace of options to process.
      rcpath: optional rcfile path if it's not stored under options.rcfile
      logger: logger instance to use

    Returns:
      Reference back to the same options passed in.

    Raises:
      ServodParserError: if -n/--name and -s/--serialname both defined
      ServodParserError: if name in options doesn't show up in servodrc
    """
    if not rcpath:
      rcpath = options.rcfile
    rcd = ServodRCParser.ParseRC(rcpath, logger=logger)
    rc = None
    if not options.serialname and options.name:
      # |name| can be set through the commandline or through an environment
      # variable. If it's set through the commandline, serialname cannot have
      # been set. However, if serialname is set and name is also set (through
      # the environment variable) name gets ignored.
      if options.name not in rcd:
        raise ServodParserError('Name %r not in rc at %r' % (options.name,
                                                             rcpath))
      rc = rcd[options.name]
      # For an rc to exist, 'sn' has to be a part of it
      setattr(options, 'serialname', rc['sn'])
    elif options.serialname:
      # srcs meaning serialname runtime configurations (rcs).
      srcs = [(name, rc) for name, rc in rcd.iteritems() if
              rc['sn'] == options.serialname]
      if srcs:
        logger.info('Found servodrc entry %r for serialname %r. Using it.',
                    srcs[0][0], options.serialname)
        rc = srcs[0][1]
    if rc:
      for elem in ['board', 'model']:
        # Unlike serialname explicit overwrites of board and model in the
        # cmdline are fine as the name flag is still useful to refer to a
        # serialname.
        if elem in rc and hasattr(options, elem):
          if not getattr(options, elem):
            logger.info('Setting %r to %r in the options as indicated by '
                        'servodrc file.', elem, rc[elem])
            setattr(options, elem, rc[elem])
          else:
            if getattr(options, elem) != rc[elem]:
              logger.warning('Ignoring rc configured %r name %r for servo %r. '
                             'Option already defined on the command line as %r',
                             elem, rc[elem], rc['sn'], getattr(options, elem))
    return options

  def parse_known_args(self, args=None, namespace=None):
    """Overwrite from Argumentparser to handle servo rc.

    Note: this also overwrites parse_args as parse_args just calls
    parse_known_args and throws an error if there's anything inside of
    xtra.

    Args:
      args: list of cmdline elements
      namespace: namespace to place the results into

    Returns:
      tuple (options, xtra) the result from parsing known args
    """
    opts, xtra = _BaseServodParser.parse_known_args(self, args=args,
                                                    namespace=namespace)
    opts = ServodRCParser.PostProcessRCElements(opts, logger=self._logger)
    return (opts, xtra)

  @staticmethod
  def ParseRC(rc_file, logger=logging):
    """Parse servodrc configuration file.

    The format of the configuration file is described above in comments to
    DEFAULT_RC_FILE. If the file is not found or is mis-formatted, a warning is
    printed but the program tries to continue.

    Args:
      rc_file: a string, name of the file storing the configuration
      logger: logger instance to use

    Returns:
      a dictionary, where keys are symbolic servo names, and values are
      dictionaries representing servo parameters read from the config file,
      keyed by strings 'sn' (for serial number), 'port', 'board', and 'model'.
    """

    if not os.path.isfile(rc_file):
      return {}
    rcd = {}  # Dictionary representing the rc file contents.
    attributes = ['name', 'sn', 'port', 'board', 'model']
    # These attributes have to be defined for a line to be valid.
    required_attributes = ['name', 'sn']
    with open(rc_file) as f:
      for rc_line in f:
        line = rc_line.split('#')[0].strip()
        if not line:
          continue
        elts = [x.strip() for x in line.split(',')]
        if len(elts) < len(required_attributes):
          logger.warning('ignoring rc line %r. Not all required '
                         'attributes defined %r.', rc_line.rstrip(),
                         required_attributes)
          continue
        # Initialize all to None that are not in elts
        line_content = dict(zip(attributes, elts + [None] * len(attributes)))
        # All required attributes are defined. Store the entry.
        name = line_content.pop('name')
        if len(elts) > len(attributes):
          extra_info = elts[len(attributes):]
          logger.warning('discarding %r for for %r', ', '.join(extra_info),
                         name)
        rcd[name] = line_content
    return rcd


class ServodClientParser(ServodRCParser):
  """Parser to use for servod client cmdline tools.

  This parser adds servoscratch serialname<>port conversion to allow
  for servod client cmdline tools to address servod using a servo device's
  serialname as well.
  """

  def __init__(self, scratch=None, **kwargs):
    """Create a ServodRCParser that has the BaseServodParser args.

    (for testing) pass a scratch directory instead of the global default.

    Args:
      scratch: scratch directory to use
      **kwargs: keyword arguments forwarded to _BaseServodParser
    """
    # BaseServodParser is used here to get the common arguments. Later,
    # the ServodClientParser adds port itself, because from a client perspective
    # there is mutual exclusion between --port/--serialname/--name as they serve
    # one purpose: to identify an instance.
    self._scratchdir = scratch
    base_parser = BaseServodParser(add_port=False, add_help=False)
    if 'parents' not in kwargs:
      kwargs['parents'] = []
    kwargs['parents'].append(base_parser)
    super(ServodClientParser, self).__init__(**kwargs)
    # Add --port to the |_id_group| to ensure exclusion with name and
    # serialname.
    BaseServodParser.AddRCEnabledPortArg(self._id_group)

  def _MapSNToPort(self, opts):
    """Helper to map the serialname in opts to the port its running on.

    Args:
      opts: ArgumentParser Namespace after parsing.

    Returns:
      opts: reference back to passed in opts

    Raises:
      Forces a program exit if |opts.serialname| is not found in the servo
      scratch
    """
    # Passing None here uses the default production logic while passing any
    # other directory can be used for testing. No need to check whether
    # |self._scratchdir| is None.
    scratch = servodutil.ServoScratch(self._scratchdir)
    try:
      entry = scratch.FindById(opts.serialname)
    except servodutil.ServodUtilError:
      self.error('No servod instance running for device with serialname: %r' %
                 opts.serialname)
    opts.port = int(entry['port'])
    return opts

  def parse_known_args(self, args=None, namespace=None):
    """Overwrite from Argumentparser to handle servo scratch logic.

    If port is not defined and serialname is defined, and serialname has
    no scratch entry, this will raise an error & terminate the program.

    If there was neither a serialname nor a port, set the port to the
    default port.

    Note: this also overwrites parse_args as parse_args just calls
    parse_known_args and throws an error if there's anything inside of
    xtra.

    Args:
      args: list of cmdline elements
      namespace: namespace to place the results into

    Returns:
      tuple (opts, xtra) the result from parsing known args
    """
    opts, xtra = _BaseServodParser.parse_known_args(self, args=args,
                                                    namespace=namespace)
    opts = ServodRCParser.PostProcessRCElements(opts, logger=self._logger)
    if opts.serialname:
      # If serialname is set, this means that either serialname or name was used
      # to find it, and therefore port cannot have been set by the user due to
      # mutual exclusion.
      opts = self._MapSNToPort(opts)
    return (opts, xtra)
