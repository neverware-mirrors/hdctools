# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common code for servo parsing support."""

import argparse
import logging
import os
import sys
import textwrap

import client
import servo_logging
import servodutil

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

  @staticmethod
  def _HandleEnvVar(cmdline, env_var, flag, pri_flags, logger, cast_type=None):
    """Look for non-defined options in the environment and add to command line.

    If |env_var| is defined in the environment and none of the variables defined
    in |pri_flags| are in the command line, then add --|flag| |$(env_var)| to
    the command line.

    Notes:
    - Modifies cmdline if name needs to be appended and an environment variable
      is defined.

    Args:
      cmdline: the list of cmdline arguments
      env_var: environment variable name to search
      flag: flag name to add the environment variable under
      pri_flags: list of flags in the cmdline that have priority over the
                 environment variable. If any found, the environment variable
                 will not be pulled in.
      logger: logger instance to use
      cast_type: optional callable to verify the environment flag is castable
                 to a desired type
    Returns:
      tuple: (cmdline, flag_added)
        cmdline - Reference back to the cmdline passed in
        flag_added - True if the flag was added, or if a collision flag was
                     found, false otherwise
    """
    if any(cl_flag in pri_flags for cl_flag in cmdline):
      return (cmdline, True)
    flag_added = False
    # If port is not defined, attempt to retrieve it from the environment.
    env_var_val = os.getenv(env_var)
    if env_var_val:
      try:
        # Casting to int first to ensure the value is int-able and suitable
        # to be a port option.
        if cast_type:
          cast_type(env_var_val)
        cmdline.extend([flag, env_var_val])
        logger.info("Adding '--%s %s' to the cmdline.", flag, env_var_val)
        flag_added = True
      except ValueError:
        logger.warning('Ignoring environment %r definition %r', env_var,
                       env_var_val)
    return (cmdline, flag_added)


class BaseServodParser(_BaseServodParser):
  """BaseServodParser handling common arguments in the servod cmdline tools."""

  def __init__(self, **kwargs):
    """Initialize by adding common arguments.

    Adds:
    - host/port arguments to find/initialize a servod instance
    - debug argument to toggle debug message printing
    - name/rcfile arguments to handle servodrc configurations

    Args:
      **kwargs: keyword arguments forwarded to _BaseServodParser
    """
    super(BaseServodParser, self).__init__(**kwargs)
    self.add_argument('-d', '--debug', action='store_true', default=False,
                      help='enable debug messages')
    self.add_argument('--host', default='localhost', type=str,
                      help='hostname of the servod server.')
    self.add_argument('-p', '--port', default=None, type=int,
                      help='port of the servod server.')

  @staticmethod
  def HandlePortEnvVar(cmdline=None, pri_flags=None, logger=logging):
    """Probe SERVOD_PORT environment variable.

    SERVOD_PORT environment variable will be used if defined and port not in
    the cmdline

    Args:
      cmdline: the list of cmdline arguments
      pri_flags: list of flags in the cmdline that have priority over the
                 environment variable. If any found, the environment variable
                 will not be pulled in.
      logger: logger instance to use

    Returns:
      tuple: (cmdline, port_defined)
        cmdline - Reference back to the cmdline passed in
        port_defined - bool showing if after this port is now in the cmdline
    """
    if not pri_flags:
      pri_flags = ['-p', '--port']
    if cmdline is None:
      cmdline = sys.argv[1:0]
    return _BaseServodParser._HandleEnvVar(cmdline=cmdline,
                                           env_var='SERVOD_PORT', flag='-p',
                                           pri_flags=pri_flags, logger=logger,
                                           cast_type=int)


class _ServodRCParser(_BaseServodParser):
  """Base class to build Servod parsers to natively handle servorc.

  This class overwrites parse_args & parse_known_args to:
  - handle SERVOD_NAME environment variable
  - parse & substitute in the servorc file on matches

  """

  def __init__(self, **kwargs):
    super(_ServodRCParser, self).__init__(**kwargs)
    self.add_argument('--rcfile', type=str, default=DEFAULT_RC_FILE,
                      help='servo description file for multi-servo operation.')
    self.add_argument('-n', '--name', type=str,
                      help='symbolic name of the servo board, '
                      'used as a config shortcut, could also be supplied '
                      'through environment variable SERVOD_NAME')

  @staticmethod
  def HandleNameEnvVar(cmdline=None, pri_flags=None, logger=logging):
    """Probe SERVOD_NAME environment variable.

    SERVOD_NAME environment variables can be used if -s/--serialname
    and --name command line switches are not set.


    Args:
      cmdline: the list of cmdline arguments
      pri_flags: list of flags in the cmdline that have priority over the
                 environment variable. If any found, the environment variable
                 will not be pulled in.
      logger: logger instance to use

    Returns:
      tuple: (cmdline, name_defined)
        cmdline - Reference back to the cmdline passed in
        name_defined - bool showing if name or serialname (a unique id)
                       is now defined in the cmdline
    """
    if not pri_flags:
      pri_flags = ['-n', '--name', '-s', '--serialname']
    if cmdline is None:
      cmdline = sys.argv[1:0]
    return _BaseServodParser._HandleEnvVar(cmdline=cmdline,
                                           env_var='SERVOD_NAME',
                                           flag='-n', pri_flags=pri_flags,
                                           logger=logger)

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
    if options.name and options.serialname:
      # NOTE(coconutruben): This is temporary until the CL that splits
      # parsing inside of servod.py removes the need for this.
      raise ServodParserError('error: argument -s/--serialname not allowed with'
                              ' argument -n/--name.')
    if not rcpath:
      rcpath = options.rcfile
    rcd = _ServodRCParser.ParseRC(rcpath, logger=logger)
    rc = None
    if options.name:
      if options.name not in rcd:
        raise ServodParserError('Name %r not in rc at %r' % (options.name,
                                                             rcpath))
      rc = rcd[options.name]
      if 'sn' in rc:
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
    args, _ = _ServodRCParser.HandleNameEnvVar(args, logger=self._logger)
    result = super(_ServodRCParser, self).parse_known_args(args=args,
                                                           namespace=namespace)
    opts, xtra = result
    opts = _ServodRCParser.PostProcessRCElements(opts, logger=self._logger)
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
    other_attributes = ['port', 'board', 'model']
    with open(rc_file) as f:
      for rc_line in f:
        line = rc_line.split('#')[0].strip()
        if not line:
          continue
        elts = [x.strip() for x in line.split(',')]
        name = elts[0]
        if not name or len(elts) < 2 or any(' ' in x for x in elts):
          logger.warning('ignoring rc line %r', rc_line.rstrip())
          continue
        rcd[name] = {'sn': elts[1]}
        # Initialize all to None
        rcd[name].update({att: None for att in other_attributes})
        rcd[name].update(dict(zip(other_attributes, elts[2:])))
        # +2 comes from name & serialname
        if len(elts) > len(other_attributes) + 2:
          extra_info = elts[len(other_attributes) + 2:]
          logger.warning('discarding %r for for %r', ', '.join(extra_info),
                         name)
    return rcd


class BaseServodRCParser(_ServodRCParser):
  """BaseServodParser extension to also natively handle servo rc config."""

  def __init__(self, **kwargs):
    """Create a ServodRCParser that has the BaseServodParser args.

    Args:
      **kwargs: keyword arguments forwarded to _BaseServodParser
    """
    base_parser = BaseServodParser(add_help=False)
    if 'parents' not in kwargs:
      kwargs['parents'] = []
    kwargs['parents'].append(base_parser)
    super(BaseServodRCParser, self).__init__(**kwargs)


class ServodClientParser(BaseServodRCParser):
  """Parser to use for servod client cmdline tools.

  This parser adds servoscratch serialname<>port conversion to allow
  for servod client cmdline tools to address servod using a servo device's
  serialname as well.
  """

  def __init__(self, **kwargs):
    """Create a ServodRCParser that has the BaseServodParser args.

    Args:
      **kwargs: keyword arguments forwarded to _BaseServodParser
    """
    super(ServodClientParser, self).__init__(**kwargs)
    self.add_argument('-s', '--serialname', default=None, type=str,
                      help='device serialname stored in eeprom. Ignored '
                           'if port is already defined.')

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
    scratch = servodutil.ServoScratch()
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
    args, _ = BaseServodParser.HandlePortEnvVar(args, logger=self._logger)
    rslt = super(ServodClientParser, self).parse_known_args(args=args,
                                                            namespace=namespace)
    opts, xtra = rslt
    if not opts.port and opts.serialname:
      # only overwrite the port if no port explicitly set
      opts = self._MapSNToPort(opts)
    if not opts.port:
      opts.port = client.DEFAULT_PORT
    return (opts, xtra)
