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

import drv.loglevel
import ftdi_common
import servo_interfaces
import servo_parsing
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
DEFAULT_PORT_RANGE = (9990, 9999)

# This text file holds servod configuration parameters. This is especially
# handy for multi servo operation.
#
# The file format is pretty loose:
#  - text starting with # is ignored til the end of the line
#  - empty lines are ignored
#  - configuration lines consist of up to 4 comma separated fields (all
#    but the first field optional):
#        servo-name, serial-number, port-number, board-name
#
#    where
#     . servo-name - a user defined symbolic name, just a reference
#                     to a certain servo board
#     . serial-number - serial number of the servo board this line pertains to
#     . port-number - desired port number for servod for this board, can be
#                     overridden by the command line switch --port or
#                     environment variable setting SERVOD_PORT
#     . board-name - board configuration file to use, can be
#                     overridden by the command line switch --board
#     . model-name - model override to use, if applicable.
#                     overridden by command line --model
#
# Since the same parameters could be defined using different means, there is a
# hierarchy of definitions:
#   command line <- environment definition <- rc config file
DEFAULT_RC_FILE = '/home/%s/.servodrc' % os.getenv('SUDO_USER', '')


class ServoDeviceWatchdog(threading.Thread):
  """Watchdog to ensure servod stops when a servo device gets lost.

  Public Attributes:
    done: event to signal that the watchdog functionality can stop

  """

  REINIT_CAPABLE = set(servo_interfaces.CCD_DEFAULTS)

  # Attempts based on REINIT_POLL_RATE that will be made to reconnect a device.
  REINIT_ATTEMPTS = 100

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
    # pylint: disable=protected-access
    self._devices = set(self._servod._devices)
    self._device_paths = {}
    usbmap = servodutil.UsbHierarchy()
    devices_not_found = set()
    for vid, pid, serial in self._devices:
      try:
        dev = servodutil.UsbHierarchy.GetUsbDevice(vid, pid, serial)
        dev_path = usbmap.GetPath(dev)
        if not dev_path:
          raise ServodError('No sysfs path found for device.')
        self._device_paths[(vid, pid, serial)] = dev_path
      # pylint: disable=broad-except
      except Exception:
        self._logger.exception(
            'Servod Watchdog ran into unexpected issue trying to find device '
            'with vid: 0x%02x pid: 0x%02x serial: %r. Device will not be '
            'tracked.', vid, pid, serial)
        devices_not_found.add((vid, pid, serial))
      if (vid, pid) in self.REINIT_CAPABLE:
        self._rate = self.REINIT_POLL_RATE
        self._logger.info('Reinit capable device found. Polling rate set '
                          'to %.2fs.', self._rate)
    # Only track devices that a sysfs path was successfully found for.
    self._devices -= devices_not_found

    # TODO(coconutruben): Here and below in addition to VID/PID also print out
    # the device type i.e. servo_micro.
    self._logger.info('Watchdog setup for devices: %s', str(self._devices))

  def run(self):
    """Poll |_devices| every |_rate| seconds. Send SIGTERM if device lost."""
    # Tokens a reinit capable device has to attempt reinit. If these run out
    # the watchdog will turn down servod.
    reinit_tokens = collections.defaultdict(lambda: self.REINIT_ATTEMPTS)
    while not self.done.is_set():
      self.done.wait(self._rate)
      for vid, pid, serial in self._devices:
        sysfs_path = self._device_paths[(vid, pid, serial)]
        if os.path.exists(sysfs_path):
          # Device was found. Make sure it's not currently being considered
          # for reinit.
          if (vid, pid, serial) in reinit_tokens:
            # Device was waiting to be reinit. Remove from token tracker.
            del reinit_tokens[(vid, pid, serial)]
            if not reinit_tokens:
              # No device waiting for reinit anymore. Issue a servod interface
              # reinitialization.
              self._servod.reinitialize()
        else:
          # Device was not found.
          if (vid, pid) in self.REINIT_CAPABLE:
            if reinit_tokens[(vid, pid, serial)]:
              # The device still has reinit tokens. Remove one.
              reinit_tokens[(vid, pid, serial)] -= 1
              self._logger.debug('Device - vid: 0x%02x pid: 0x%02x serial: %r '
                                 'not found when polling. Device is marked as '
                                 'reinit capable. %d more reinit attempts '
                                 'before giving up.', vid, pid, serial,
                                 reinit_tokens[(vid, pid, serial)])
              # pylint: disable=protected-access
              # Indicate to servod that interfaces are unavailable.
              self._servod._ifaces_available.clear()
              continue
          # Device was not found, thus signaling to end servod.
          self._logger.error('Device - vid: 0x%02x pid: 0x%02x serial: %r - '
                             'not found when polling. Turning down servod.',
                             vid, pid, serial)
          # Watchdog should run in the same process as servod thread.
          os.kill(os.getpid(), signal.SIGTERM)
          self.done.set()
          break


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
  except usb.USBError, e:
    # TODO(tbroch) other non-FTDI devices on my host cause following msg
    #   usb.USBError: error sending control message: Broken pipe
    # Need to investigate further
    pass
  except Exception:
    # This was causing servod to fail to start in the presence of
    # a broken usb interface.
    self._logger.exception('usb_get_iserial failed in an unknown way')
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
    options = self._parse_args(cmdline)
    if options.debug:
      level = 'debug'
    else:
      level = drv.loglevel.DEFAULT_LOGLEVEL

    loglevel, fmt = drv.loglevel.LOGLEVEL_MAP[level]
    logging.basicConfig(level=loglevel, format=fmt)

    # Servod needs to be running in the chroot without PID namespaces in order
    # to freeze terminals when reading from the UARTs.
    terminal_freezer.CheckForPIDNamespace()

    self._logger = logging.getLogger(os.path.basename(sys.argv[0]))
    self._logger.info('Start')
    # The scratch initialization here ensures that potentially stale entries
    # are removed from the scratch before attempting to create a new one.
    self._scratchutil = servodutil.ServoScratch()

    servo_parsing.get_env_options(self._logger, options)

    if options.name and options.serialname:
      self._logger.error("Mutually exclusive '--name' or '--serialname' is "
                         'allowed')
      sys.exit(-1)

    servo_device = self.discover_servo(options,
                                       servo_parsing.parse_rc(self._logger,
                                                              options.rcfile))
    if not servo_device:
      sys.exit(-1)

    self._host = options.host
    lot_id = self.get_lot_id(servo_device)
    board_version = self.get_board_version(lot_id, servo_device.idProduct)
    self._logger.debug('board_version = %s', board_version)
    all_configs = []
    if not options.noautoconfig:
      all_configs += self.get_auto_configs(board_version)

    if options.config:
      for config in options.config:
        # quietly ignore duplicate configs for backwards compatibility
        if config not in all_configs:
          all_configs.append(config)

    if not all_configs:
      raise ServodError('No automatic config found,'
                        ' and no config specified with -c <file>')

    scfg = system_config.SystemConfig()

    if options.board:
      # Handle differentiated model case.
      board_config = None
      if options.model:
        board_config = 'servo_%s_%s_overlay.xml' % (
            options.board, options.model)

        if not scfg.find_cfg_file(board_config):
          self._logger.info('No XML overlay for model '
              '%s, falling back to board %s default',
              options.model, options.board)
          board_config = None
        else:
          self._logger.info('Found XML overlay for model %s:%s',
                            options.board, options.model)

      # Handle generic board config.
      if not board_config:
        board_config = 'servo_' + options.board + '_overlay.xml'
        if not scfg.find_cfg_file(board_config):
          self._logger.error('No XML overlay for board %s', options.board)
          sys.exit(-1)

        self._logger.info('Found XML overlay for board %s', options.board)

      all_configs.append(board_config)

    for cfg_file in all_configs:
      scfg.add_cfg_file(cfg_file)

    self._logger.debug('\n%s', scfg.display_config())

    self._logger.debug('Servo is vid:0x%04x pid:0x%04x sid:%s',
                       servo_device.idVendor, servo_device.idProduct,
                       usb_get_iserial(servo_device))

    if options.port:
      start_port = options.port
      end_port = options.port
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
      if options.port:
        err_msg = ('Port %d is busy' % options.port)
      else:
        err_msg = ('Could not find a free port in %d..%d range' % (end_port,
                                                                   start_port))

      self._logger.fatal(err_msg)
      sys.exit(-1)

    self._servod = servo_server.Servod(
        scfg, vendor=servo_device.idVendor, product=servo_device.idProduct,
        serialname=usb_get_iserial(servo_device),
        interfaces=options.interfaces.split(), board=options.board,
        model=options.model, version=board_version, usbkm232=options.usbkm232)

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
      args: argparse Namespace after parsing & processing cmdline
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
    # BaseServodParser adds port, host, debug args & name/rcfile args for rc.
    parser = servo_parsing.BaseServodParser(description=description,
                                            examples=examples,
                                            version='%(prog)s ' + VERSION)
    parser.add_argument('--vendor', default=None, type=lambda x: int(x,0),
                        help='vendor id of device to interface to')
    parser.add_argument('--product', default=None, type=lambda x: int(x,0),
                        help='USB product id of device to interface with')
    parser.add_argument('-s', '--serialname', default=None, type=str,
                        help='device serialname stored in eeprom')
    parser.add_argument('-c', '--config', default=None, type=str,
                        action='append', help='system config file (XML) to '
                                              'read')
    parser.add_argument('-b', '--board', default=None, type=str, action='store',
                        help='include config file (XML) for given board')
    parser.add_argument('-m', '--model', default='', type=str, action='store',
                        help='optional config for a model of the given board, '
                        'requires --board')
    parser.add_argument('--noautoconfig', action='store_true', default=False,
                        help='Disable automatic determination of config files')
    parser.add_argument('-i', '--interfaces', type=str, default='',
                        help='ordered space-delimited list of interfaces. '
                        'Valid choices are gpio|i2c|uart|gpiouart|dummy')
    parser.add_argument('-u', '--usbkm232', type=str,
                        help='path to USB-KM232 device which allow for '
                        'sending keyboard commands to DUTs that do not '
                        'have built in keyboards. Used in FAFT tests. '
                        '(Optional), e.g. /dev/ttyUSB0')
    servo_parsing.add_servo_parsing_rc_options(parser)
    return parser.parse_args(cmdline)

  def find_servod_match(self, options, all_servos, servodrc):
    """Find a servo matching one of servodrc lines.

    Given a list of servod objects matching discovered servos, display the list
    to the user and check if there is a configuration file line corresponding to
    one of the servos.

    If a line like that exists, and it includes options which are not yet
    defined in the options object - set these options' values. If the option is
    already defined - report that this config line setting is ignored.

    Args:
      options: an options object as returned by parse_options
      all_servos: a list of servod objects corresponding to discovered servo
                  devices
      servodrc: a dictionary representing the contents of the servodrc file, as
                returned by parse_rc() above (if any)

    Returns:
      a matching servod object, if found, None otherwise

    Raises:
      ServodError: in case required name is not found in the config file
    """

    for servo in all_servos:
      self._logger.info('Found servo, vid: 0x%04x pid: 0x%04x sid: %s',
                        servo.idVendor, servo.idProduct, usb_get_iserial(servo))

    # If user specified servod name in the command line - match it to the serial
    # number.

    if options.name:
      config = servodrc.get(options.name)
      if not config:
        raise ServodError("Name '%s' not in the config file" % options.name)
      options.serialname = config['sn']
    elif options.serialname:
      # Let's try finding config for a serial name
      for config in servodrc.itervalues():
        if config['sn'] == options.serialname:
          break
      else:
        return None

    if not options.serialname:
      # There is nothing to match
      return None

    for servo in all_servos:
      servo_sn = usb_get_iserial(servo)
      if servo_sn != options.serialname:
        continue

      # Match found, some sanity checks/updates before using it
      matching_servo = servo
      rc_port = config['port']
      if rc_port:
        if not options.port:
          options.port = rc_port
        elif options.port != rc_port:
          self._logger.warning('Ignoring rc configured port %s for servo %s',
                               rc_port, servo_sn)

      rc_board = config['board']
      if rc_board:
        if not options.board:
          options.board = rc_board
        elif options.board != rc_board:
          self._logger.warning('Ignoring rc configured board name %s for servo '
                               '%s', rc_board, servo_sn)
      if 'model' in config:
        rc_model = config['model']
        if not options.model:
          options.model = rc_model
        elif options.model != rc_model:
          self._logger.warning('Ignoring rc configured model name %s for servo '
                               '%s', rc_model, servo_sn)
      return matching_servo

    raise ServodError('No matching servo found')

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

  def discover_servo(self, options, servodrc):
    """Find a servo USB device to use.

    First, find all servo devices matching command line options, this may result
    in discovering none, one or more devices.

    Then try matching discovered servos and the configuration defined in
    servodrc. A match this will result in reading missing options from servodrc
    file.

    If there is a match - return the matching device.

    If no match found, but there is only one servo connected - return it. If
    there is no match found and multiple servos are connected - report an error
    and return None.

    Args:
      options: the options object returned by opt_parse
      servodrc: a dictionary representing the contents of the servodrc file, as
                returned by parse_rc() above (if any)
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

    # See if there is a matching entry in servodrc
    matching_servo = self.find_servod_match(options, all_servos, servodrc)

    if matching_servo:
      return matching_servo

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
    # pylint: disable=protected-access, invalid-name, unused-variable
    # current method of retrieving device information requires this
    serials = [serial for _vid, _pid, serial in self._servod._devices]
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
