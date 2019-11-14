#!/usr/bin/env python2
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Python version of Servo hardware debug & control board server."""

# pylint: disable=g-bad-import-order
# pkg_resources is erroneously suggested to be in the 3rd party segment
import collections
import errno
import logging
import os
import pkg_resources
import select
import signal
import SimpleXMLRPCServer
import socket
import sys
import threading
import time

import ftdi_common
import servo_interfaces
import servo_logging
import servo_parsing
import servo_postinit
import servo_server
import servodutil
import system_config
import terminal_freezer
import usb

VERSION = pkg_resources.require('servo')[0].version

MAX_ISERIAL_STR = 128

# If user does not specify a port to use, try ports in this range. Traverse
# the range from high to low addresses to maintain backwards compatibility
# (the first checked default port is 9999, the range is such that all possible
# port numbers are 4 digits).
DEFAULT_PORT_RANGE = (9980, 9999)


class ServoDeviceWatchdog(threading.Thread):
  """Watchdog to ensure servod stops when a servo device gets lost.

  Public Attributes:
    done: event to signal that the watchdog functionality can stop

  """

  # Rate in seconds used to poll when a reinit capable device is attached.
  REINIT_POLL_RATE = 0.1

  def __init__(self, servod, poll_rate=1.0):
    """Setup watchdog thread.

    Args:
      servod: servod server the watchdog is watching over.
      poll_rate: poll rate in seconds
    """
    threading.Thread.__init__(self)
    self._logger = logging.getLogger(type(self).__name__)
    self.done = threading.Event()
    self._servod = servod
    self._rate = poll_rate
    self._devices = []

    for device in self._servod.get_devices():
      self._devices.append(device)
      if device.reinit_ok():
        self._rate = self.REINIT_POLL_RATE
        self._logger.info('Reinit capable device found. Polling rate set '
                          'to %.2fs.', self._rate)

    # TODO(coconutruben): Here and below in addition to VID/PID also print out
    # the device type i.e. servo_micro.
    self._logger.info('Watchdog setup for devices: %s', self._devices)

  def run(self):
    """Poll |_devices| every |_rate| seconds. Send SIGTERM if device lost."""
    # Devices that need to be reinitialized
    disconnected_devices = {}
    while not self.done.is_set():
      self.done.wait(self._rate)
      for device in self._devices:
        dev_id = device.get_id()
        if device.is_connected():
          # Device was found. If it is in the disconnected devices, then it
          # needs to be reinitialized. If no devices are disconnected,
          # reinitialize all devices.
          reinit_needed = disconnected_devices.pop(dev_id, None)
          if reinit_needed and not disconnected_devices:
            self._servod.reinitialize()
        else:
          # Device was not found.
          self._logger.debug('Device - %s not found when polling.', device)
          if not device.reinit_ok():
            # Device was not found and we can't reinitialize it. End servod.
            self._logger.error('Device - %s - Turning down servod.', device)
            # Watchdog should run in the same process as servod thread.
            os.kill(os.getpid(), signal.SIGTERM)
            self.done.set()
            break
          disconnected_devices[dev_id] = 1
          device.disconnect()


def usb_get_iserial(device):
  """Get USB device's iSerial string.

  Args:
    device: usb.Device object

  Returns:
    iserial: USB devices iSerial string or empty string if the device has
             no serial number.
  """
  # pylint: disable=broad-except
  device_handle = device.open()
  # The device has no serial number string descriptor.
  if device.iSerialNumber == 0:
    return ''
  iserial = ''
  try:
    iserial = device_handle.getString(device.iSerialNumber, MAX_ISERIAL_STR)
  except usb.USBError:
    # TODO(tbroch) other non-FTDI devices on my host cause following msg
    #   usb.USBError: error sending control message: Broken pipe
    # Need to investigate further
    pass
  except Exception:
    # This was causing servod to fail to start in the presence of
    # a broken usb interface.
    logging.exception('usb_get_iserial failed in an unknown way')
  return iserial


def usb_find(vendor, product, serialname):
  """Find USB devices based on vendor, product and serial identifiers.

  Locates all USB devices that match the criteria of the arguments.  In the
  case where input arguments are 'None' that argument is a don't care

  Args:
    vendor: USB vendor id (integer)
    product: USB product id (integer)
    serialname: USB serial id (string)

  Returns:
    matched_devices : list of pyusb devices matching input args
  """
  matched_devices = []
  for bus in usb.busses():
    for device in bus.devices:
      if (not vendor or device.idVendor == vendor) and \
            (not product or device.idProduct == product) and \
            (not serialname or usb_get_iserial(device).endswith(serialname)):
        matched_devices.append(device)
  return matched_devices


# pylint: disable=g-bad-exception-name
class ServodError(Exception):
  """Exception class for servod server."""
  pass


class ServodStarter(object):
  """Class to manage servod instance and rpc server its being served on."""

  def __init__(self, cmdline):
    """Prepare servod invocation.

    Parse cmdline and prompt user for missing information if necessary to start
    servod. Prepare servod instance & thread for it to be served from.

    Args:
      cmdline: list, cmdline components to parse

    Raises:
      ServodError: if automatic config cannot be found
    """
    # The scratch initialization here ensures that potentially stale entries
    # are removed from the scratch before attempting to create a new one.
    self._scratchutil = servodutil.ServoScratch()
    # Initialize logging up here first to ensure log messages from parsing
    # can go through.
    loglevel, fmt = servo_logging.LOGLEVEL_MAP[servo_logging.DEFAULT_LOGLEVEL]
    logging.basicConfig(loglevel=loglevel, format=fmt)
    self._logger = logging.getLogger(os.path.basename(sys.argv[0]))
    sopts, devopts = self._parse_args(cmdline)
    self._host = sopts.host

    if servo_parsing.ArgMarkedAsUserSupplied(sopts, 'port'):
      start_port = sopts.port
      end_port = sopts.port
    else:
      end_port, start_port = DEFAULT_PORT_RANGE
    for self._servo_port in xrange(start_port, end_port - 1, -1):
      try:
        self._server = SimpleXMLRPCServer.SimpleXMLRPCServer((self._host,
                                                              self._servo_port),
                                                             logRequests=False)
        break
      except socket.error as e:
        if e.errno == errno.EADDRINUSE:
          continue  # Port taken, see if there is another one next to it.
        self._logger.fatal("Problem opening Server's socket: %s", e)
        sys.exit(-1)
    else:
      if start_port == end_port:
        # This condition indicates that a specific port was being requested.
        # Report that the port itself is busy.
        err_msg = ('Port %d is busy' % sopts.port)
      else:
        err_msg = ('Could not find a free port in %d..%d range' % (end_port,
                                                                   start_port))

      self._logger.fatal(err_msg)
      sys.exit(-1)
    servo_logging.setup(logdir=sopts.log_dir, port=self._servo_port,
                        debug_stdout=sopts.debug)

    if sopts.dual_v4:
      # Leave the right breadcrumbs for servo_postinit to know whether to setup
      # a dual instance or not.
      os.environ[servo_postinit.DUAL_V4_VAR] = servo_postinit.DUAL_V4_VAR_DUMMY

    # Servod needs to be running in the chroot without PID namespaces in order
    # to freeze terminals when reading from the UARTs.
    terminal_freezer.CheckForPIDNamespace()

    self._logger.info('Start')

    servo_device = self.discover_servo(devopts)
    if not servo_device:
      sys.exit(-1)

    lot_id = self.get_lot_id(servo_device)
    board_version = self.get_board_version(lot_id, servo_device.idProduct)
    self._logger.debug('board_version = %s', board_version)
    all_configs = []
    if not devopts.noautoconfig:
      all_configs += self.get_auto_configs(board_version)

    if devopts.config:
      for config in devopts.config:
        # quietly ignore duplicate configs for backwards compatibility
        if config not in all_configs:
          all_configs.append(config)

    if not all_configs:
      raise ServodError('No automatic config found,'
                        ' and no config specified with -c <file>')

    scfg = system_config.SystemConfig()

    if devopts.board:
      # Handle differentiated model case.
      board_config = None
      if devopts.model:
        board_config = 'servo_%s_%s_overlay.xml' % (
            devopts.board, devopts.model)

        if not scfg.find_cfg_file(board_config):
          self._logger.info('No XML overlay for model '
                            '%s, falling back to board %s default',
                            devopts.model, devopts.board)
          board_config = None
        else:
          self._logger.info('Found XML overlay for model %s:%s',
                            devopts.board, devopts.model)

      # Handle generic board config.
      if not board_config:
        board_config = 'servo_' + devopts.board + '_overlay.xml'
        if not scfg.find_cfg_file(board_config):
          self._logger.error('No XML overlay for board %s', devopts.board)
          sys.exit(-1)

        self._logger.info('Found XML overlay for board %s', devopts.board)

      all_configs.append(board_config)
      scfg.set_board_cfg(board_config)

    for cfg_file in all_configs:
      scfg.add_cfg_file(cfg_file)

    self._logger.debug('\n%s', scfg.display_config())

    self._logger.debug('Servo is vid:0x%04x pid:0x%04x sid:%s',
                       servo_device.idVendor, servo_device.idProduct,
                       usb_get_iserial(servo_device))

    self._servod = servo_server.Servod(
        scfg, vendor=servo_device.idVendor, product=servo_device.idProduct,
        serialname=usb_get_iserial(servo_device),
        interfaces=devopts.interfaces.split(), board=devopts.board,
        model=devopts.model, version=board_version, usbkm232=devopts.usbkm232)

    # Small timeout to allow interface threads to initialize.
    time.sleep(0.5)

    self._servod.hwinit(verbose=True)
    self._server.register_introspection_functions()
    self._server.register_multicall_functions()
    self._server.register_instance(self._servod)
    self._server_thread = threading.Thread(target=self._serve)
    self._server_thread.daemon = True
    self._turndown_initiated = False
    # pylint: disable=protected-access
    # Needs access to the servod instance.
    self._watchdog_thread = ServoDeviceWatchdog(self._servod)
    self._exit_status = 0

  def handle_sig(self, signum):
    """Handle a signal by turning off the server & cleaning up servod."""
    if not self._turndown_initiated:
      self._turndown_initiated = True
      self._logger.info('Received signal: %d. Attempting to turn off', signum)
      self._server.shutdown()
      self._server.server_close()
      self._servod.close()
      self._logger.info('Successfully turned off')

  def _parse_args(self, cmdline):
    """Parse commandline arguments.

    Args:
      cmdline: list of cmdline arguments

    Returns:
      tuple: (server, dev) args Namespaces after parsing & processing cmdline
        server: holds --port, --host, --log-dir, --allow-dual-v4, --debug flags
        dev: holds all the device flags (serialname, interfaces, configs etc -
             see below) necessary to configure a servo device.
    """
    description = (
        '%(prog)s is server to interact with servo debug & control board. '
        'This server communicates to the board via USB and the client via '
        'xmlrpc library. Launcher most specify at least one --config <file> '
        'in order for the server to provide any functionality. In most cases, '
        'multiple configs will be needed to expose complete functionality '
        'between debug & DUT board.')
    examples = [('-c <path>/data/servo.xml',
                 'Launch server on default host:port with native servo config'),
                ('-c <file> -p 8888', 'Launch server listening on port 8888'),
                ('-c <file> --vendor 0x18d1 --product 0x5001',
                 'Launch targetting usb device with vid:pid == 0x18d1:0x5001 '
                 '(Google/Servo)')]
    version = '%(prog)s ' + VERSION
    # BaseServodParser adds port, host, debug args.
    server_pars = servo_parsing.BaseServodParser(version=version,
                                                 add_help=False)
    server_pars.add_argument('--log-dir', type=str, default=None,
                             const='/var/log/', nargs='?',
                             help='path where to dump servod debug logs as a '
                             'file. If flag omitted in command line, no logs '
                             'will be dumped to a file.')
    server_pars.add_argument('--allow-dual-v4', dest='dual_v4', default=False,
                             action='store_true',
                             help='Allow dual micro and ccd on servo v4.')
    # ServodRCParser adds configs for -name/-rcfile & serialname & parses them.
    dev_pars = servo_parsing.ServodRCParser(add_help=False)
    dev_pars.add_argument('--vendor', default=None, type=lambda x: int(x, 0),
                          help='vendor id of device to interface to')
    dev_pars.add_argument('--product', default=None, type=lambda x: int(x, 0),
                          help='USB product id of device to interface with')
    dev_pars.add_argument('-c', '--config', default=None, type=str,
                          action='append', help='system config file (XML) to '
                                                'read')
    dev_pars.add_argument('-b', '--board', default='', type=str,
                          action='store', help='include config file (XML) for '
                                               'given board')
    dev_pars.add_argument('-m', '--model', default='', type=str, action='store',
                          help='optional config for a model of the given board,'
                          ' requires --board')
    dev_pars.add_argument('--noautoconfig', action='store_true', default=False,
                          help='Disable automatic determination of config '
                               'files')
    dev_pars.add_argument('-i', '--interfaces', type=str, default='',
                          help='ordered space-delimited list of interfaces. '
                               'Valid choices are gpio|i2c|uart|gpiouart|dummy')
    dev_pars.add_argument('-u', '--usbkm232', type=str,
                          help='path to USB-KM232 device which allow for '
                               'sending keyboard commands to DUTs that do not '
                               'have built in keyboards. Used in FAFT tests. '
                               '(Optional), e.g. /dev/ttyUSB0')
    # Create a unified parser with both server & device arguments to display
    # meaningful help messages to the user.
    # pylint: disable=protected-access
    # The parser here is used for its base ability to format examples.
    help_displayer = servo_parsing._BaseServodParser(description=description,
                                                     examples=examples,
                                                     parents=[server_pars,
                                                              dev_pars])
    if any([True for argstr in cmdline if argstr in ['-h', '--help']]):
      help_displayer.print_help()
      help_displayer.exit()
    server_args, dev_cmdline = server_pars.parse_known_args(cmdline)
    dev_args = dev_pars.parse_args(dev_cmdline)
    return (server_args, dev_args)

  def choose_servo(self, all_servos):
    """Let user choose a servo from available list of unique devices.

    Args:
      all_servos: a list of servod objects corresponding to discovered servo
                  devices

    Returns:
      servo object for the matching (or single) device, otherwise None
    """
    self._logger.info('')
    for i, servo in enumerate(all_servos):
      self._logger.info("Press '%d' for servo, vid: 0x%04x pid: 0x%04x sid: %s",
                        i, servo.idVendor, servo.idProduct,
                        usb_get_iserial(servo))

    (rlist, _, _) = select.select([sys.stdin], [], [], 10)
    if not rlist:
      self._logger.warn('Timed out waiting for your choice\n')
      return None

    rsp = rlist[0].readline().strip()
    try:
      rsp = int(rsp)
    except ValueError:
      self._logger.warn('%s not a valid choice ... ignoring', rsp)
      return None

    if rsp < 0 or rsp >= len(all_servos):
      self._logger.warn('%s outside of choice range ... ignoring', rsp)
      return None

    logging.info('')
    servo = all_servos[rsp]
    logging.info('Chose %d ... starting servod on servo '
                 'vid: 0x%04x pid: 0x%04x sid: %s', rsp, servo.idVendor,
                 servo.idProduct, usb_get_iserial(servo))
    logging.info('')
    return servo

  def discover_servo(self, options):
    """Find a servo USB device to use.

    First, find all servo devices matching command line options, this may result
    in discovering none, one or more devices.

    If there is a match - return the matching device.

    If there is only one servo connected - return it.
    If there is no match found and multiple servos are connected - report an
    error and return None.

    Args:
      options: the options object returned by arg_parse

    Returns:
      servo object for the matching (or single) device, otherwise None
    """

    vendor, product, serialname = (options.vendor, options.product,
                                   options.serialname)
    all_servos = []
    for (vid, pid) in servo_interfaces.SERVO_ID_DEFAULTS:
      if (vendor and vendor != vid) or \
            (product and product != pid):
        continue
      all_servos.extend(usb_find(vid, pid, serialname))

    if not all_servos:
      self._logger.error('No servos found')
      return None

    if len(all_servos) == 1:
      return all_servos[0]

    # See if only one primary servo. Filter secordary servos, like servo-micro.
    secondary_servos = (
        servo_interfaces.SERVO_MICRO_DEFAULTS + servo_interfaces.CCD_DEFAULTS)
    all_primary_servos = [
        servo for servo in all_servos
        if (servo.idVendor, servo.idProduct) not in secondary_servos
    ]
    if len(all_primary_servos) == 1:
      return all_primary_servos[0]

    # Let user choose a servo
    matching_servo = self.choose_servo(all_servos)
    if matching_servo:
      return matching_servo

    self._logger.error('Use --vendor, --product or --serialname switches to '
                       'identify servo uniquely, or create a servodrc file '
                       'and use the --name switch')

    return None

  def get_board_version(self, lot_id, product_id):
    """Get board version string.

    Typically this will be a string of format <boardname>_<version>.
    For example, servo_v2.

    Args:
      lot_id: string, identifying which lot device was fabbed from or None
      product_id: integer, USB product id

    Returns:
      board_version: string, board & version or None if not found
    """
    if lot_id:
      for (board_version, lot_ids) in \
            ftdi_common.SERVO_LOT_ID_DEFAULTS.iteritems():
        if lot_id in lot_ids:
          return board_version

    for (board_version, vids) in \
          ftdi_common.SERVO_PID_DEFAULTS.iteritems():
      if product_id in vids:
        return board_version

    return None

  def get_lot_id(self, servo):
    """Get lot_id for a given servo.

    Args:
      servo: usb.Device object

    Returns:
      lot_id of the servo device.
    """
    lot_id = None
    iserial = usb_get_iserial(servo)
    self._logger.debug('iserial = %s', iserial)
    if not iserial:
      self._logger.warn('Servo device has no iserial value')
    else:
      try:
        (lot_id, _) = iserial.split('-')
      except ValueError:
        self._logger.warn("Servo device's iserial was unrecognized.")
    return lot_id

  def get_auto_configs(self, board_version):
    """Get xml configs that should be loaded.

    Args:
      board_version: string, board & version

    Returns:
      configs: list of XML config files that should be loaded
    """
    if board_version not in ftdi_common.SERVO_CONFIG_DEFAULTS:
      self._logger.warning('Unable to determine configs to load for board '
                           'version = %s', board_version)
      return []
    return ftdi_common.SERVO_CONFIG_DEFAULTS[board_version]

  def cleanup(self):
    """Perform any cleanup related work after servod server shut down."""
    self._scratchutil.RemoveEntry(self._servo_port)
    self._logger.info('Server on %s port %s turned down', self._host,
                      self._servo_port)
    servo_logging.cleanup()

  def _serve(self):
    """Wrapper around rpc server's serve_forever to catch server errors."""
    # pylint: disable=broad-except
    self._logger.info('Listening on %s port %s', self._host, self._servo_port)
    try:
      self._server.serve_forever()
    except Exception:
      self._exit_status = 1

  def serve(self):
    """Add signal handlers, start servod on its own thread & wait for signal.

    Intercepts and handles stop signals so shutdown is handled.
    """
    handler = lambda signal, unused, starter=self: starter.handle_sig(signal)
    stop_signals = [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT,
                    signal.SIGTERM, signal.SIGTSTP]
    for ss in stop_signals:
      signal.signal(ss, handler)
    serials = set(self._servod.get_servo_serials().values())
    try:
      self._scratchutil.AddEntry(self._servo_port, serials, os.getpid())
    except servodutil.ServodUtilError:
      self._servod.close()
      sys.exit(1)
    self._watchdog_thread.start()
    self._server_thread.start()
    signal.pause()
    # Set watchdog thread to end
    self._watchdog_thread.done.set()
    # Collect servo and watchdog threads
    self._server_thread.join()
    self._watchdog_thread.join()
    self.cleanup()
    sys.exit(self._exit_status)


# pylint: disable=dangerous-default-value
# Ability to pass an arbitrary or artifical cmdline for testing is desirable.
def main(cmdline=sys.argv[1:]):
  try:
    starter = ServodStarter(cmdline)
  except ServodError as e:
    print 'Error: ', e.message
    sys.exit(1)
  starter.serve()

if __name__ == '__main__':
  main()
