# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo Server."""
import datetime
import fcntl
import fnmatch
import logging
import os
import re
import SimpleXMLRPCServer
import threading
import time
import usb

import drv as servo_drv
import bbadc
import bbi2c
import bbgpio
import bbuart
import ec3po_interface
import ftdigpio
import ftdii2c
import ftdi_common
import ftdiuart
import i2cbus
import keyboard_handlers
import servo_interfaces
import servo_postinit
import stm32gpio
import stm32i2c
import stm32uart

HwDriverError = servo_drv.hw_driver.HwDriverError

MAX_I2C_CLOCK_HZ = 100000


class ServodError(Exception):
  """Exception class for servod."""


class Servod(object):
  """Main class for Servo debug/controller Daemon."""

  # This is the key to get the main serial used in the _serialnames dict.
  MAIN_SERIAL = 'main'
  SERVO_MICRO_SERIAL = 'servo_micro'
  CCD_SERIAL = 'ccd'

  # Timeout to wait for interfaces to become available again if reinitialization
  # is taking place. In seconds.
  INTERFACE_AVAILABILITY_TIMEOUT = 60

  def init_servo_interfaces(self, vendor, product, serialname, interfaces):
    """Init the servo interfaces with the given interfaces.

    We don't use the self._{vendor,product,serialname} attributes because we
    want to allow other callers to initialize other interfaces that may not
    be associated with the initialized attributes (e.g. a servo v4 servod object
    that wants to also initialize a servo micro interface).

    Args:
      vendor: USB vendor id of FTDI device.
      product: USB product id of FTDI device.
      serialname: String of device serialname/number as defined in FTDI
          eeprom.
      interfaces: List of strings of interface types the server will
          instantiate.

    Raises:
      ServodError if unable to locate init method for particular interface.
    """
    # If it is a new device add it to the list
    device = (vendor, product, serialname)
    if device not in self._devices:
      self._devices.append(device)

    # Extend the interface list if we need to.
    interfaces_len = len(interfaces)
    interface_list_len = len(self._interface_list)
    if interfaces_len > interface_list_len:
      self._interface_list += [None] * (interfaces_len - interface_list_len)

    for i, interface in enumerate(interfaces):
      is_ftdi_interface = False
      if type(interface) is dict:
        name = interface['name']
        # Store interface index for those that care about it.
        interface['index'] = i
      elif type(interface) is str and interface != 'dummy':
        name = interface
        # It's a FTDI related interface. #0 is reserved for no use.
        interface = ((i - 1) % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE) + 1
        is_ftdi_interface = True
      elif type(interface) is str and interface == 'dummy':
        # 'dummy' reserves the interface for future use.  Typically the
        # interface will be managed by external third-party tools like
        # openOCD for JTAG or flashrom for SPI.  In the case of servo V4,
        # it serves as a placeholder for servo micro interfaces.
        continue
      else:
        raise ServodError('Illegal interface type %s' % type(interface))

      # servos with multiple FTDI are guaranteed to have contiguous USB PIDs
      product_increment = 0
      if is_ftdi_interface:
        product_increment = (i - 1) / ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE
        if product_increment:
          self._logger.info('Use the next FTDI part @ pid = 0x%04x',
                            product + product_increment)

      self._logger.info('Initializing interface %d to %s', i, name)
      try:
        func = getattr(self, '_init_%s' % name)
      except AttributeError:
        raise ServodError('Unable to locate init for interface %s' % name)
      result = func(vendor, product + product_increment, serialname, interface)

      if isinstance(result, tuple):
        result_len = len(result)
        self._interface_list[i:(i + result_len)] = result
      else:
        self._interface_list[i] = result

  def __init__(self, config, vendor, product, serialname=None, interfaces=None,
               board='', version=None, usbkm232=None):
    """Servod constructor.

    Args:
      config: instance of SystemConfig containing all controls for
          particular Servod invocation
      vendor: usb vendor id of FTDI device
      product: usb product id of FTDI device
      serialname: string of device serialname/number as defined in FTDI eeprom.
      interfaces: list of strings of interface types the server will instantiate
      version: String. Servo board version. Examples: servo_v1, servo_v2,
          servo_v2_r0, servo_v3
      usbkm232: String. Optional. Path to USB-KM232 device which allow for
          sending keyboard commands to DUTs that do not have built in
          keyboards. Used in FAFT tests. Use None for on board AVR MCU.
          e.g. '/dev/ttyUSB0' or None.

    Raises:
      ServodError: if unable to locate init method for particular interface
    """
    self._logger = logging.getLogger('Servod')
    self._logger.debug('')
    self._ifaces_available = threading.Event()
    # Initially interfaces should be available.
    self._ifaces_available.set()
    self._vendor = vendor
    self._product = product
    self._devices = []
    self._serialnames = {self.MAIN_SERIAL: serialname}
    self._syscfg = config
    # list of objects (Fi2c, Fgpio) to physical interfaces (gpio, i2c) that ftdi
    # interfaces are mapped to
    self._interface_list = []
    # Dict of Dict to map control name, function name to to tuple (params, drv)
    # Ex) _drv_dict[name]['get'] = (params, drv)
    self._drv_dict = {}
    self._board = board
    self._base_board = ''
    self._version = version
    self._usbkm232 = usbkm232
    if not interfaces:
      try:
        interfaces = servo_interfaces.INTERFACE_BOARDS[board][vendor][product]
      except KeyError:
        interfaces = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]
    self._interfaces = interfaces

    self.init_servo_interfaces(vendor, product, serialname, interfaces)
    servo_postinit.post_init(self)

  def reinitialize(self):
    """Reinitialize all interfaces that support reinitialization"""
    for i, interface in enumerate(self._interface_list):
      if hasattr(interface, 'reinitialize'):
        interface.reinitialize()
      else:
        self._logger.debug('interface %d has no reset functionality', i)
    # Indicate interfaces are safe to use again.
    self._ifaces_available.set()

  def get_servo_interfaces(self, position, size):
    """Get the list of servo interfaces.

    Args:
      position: The index the first interface to get.
      size: The number of the interfaces.
    """
    return self._interface_list[position:(position + size)]

  def set_servo_interfaces(self, position, interfaces):
    """Set the list of servo interfaces.

    Args:
      position: The index the first interface to set.
      interfaces: The list of interfaces to set.
    """
    size = len(interfaces)
    self._interface_list[position:(position + size)] = interfaces

  def _init_keyboard_handler(self, servo, board=''):
    """Initialize the correct keyboard handler for board.

    Args:
      servo: servo object.
      board: string, board name.

    Returns:
      keyboard handler object, or None if no keyboard supported.
    """
    if board == 'parrot':
      return keyboard_handlers.ParrotHandler(servo)
    elif board == 'stout':
      return keyboard_handlers.StoutHandler(servo)
    elif board in ('buddy', 'cranky', 'guado', 'jecht', 'mccloud', 'monroe',
                   'ninja', 'nyan_kitty', 'panther', 'rikku', 'stumpy', 'sumo',
                   'tidus', 'tricky', 'veyron_fievel', 'veyron_mickey',
                   'veyron_rialto', 'veyron_tiger', 'zako'):
      if self._usbkm232 is None:
        logging.info('No device path specified for usbkm232 handler. Use '
                     'the servo atmega chip to handle.')

        # Use servo onboard keyboard emulator.
        if not self._syscfg.is_control('atmega_rst'):
          logging.warn('No atmega in servo board. So no keyboard support.')
          return None

        self.set('atmega_rst', 'on')
        self.set('at_hwb', 'off')
        self.set('atmega_rst', 'off')
        self._usbkm232 = self.get('atmega_pty')

        # We don't need to set the atmega uart settings if we're a servo v4.
        if 'servo_v4' not in self._version:
          self.set('atmega_baudrate', '9600')
          self.set('atmega_bits', 'eight')
          self.set('atmega_parity', 'none')
          self.set('atmega_sbits', 'one')
          self.set('usb_mux_sel4', 'on')
          self.set('usb_mux_oe4', 'on')
          # Allow atmega bootup time.
          time.sleep(1.0)

      self._logger.info('USBKM232: %s', self._usbkm232)
      return keyboard_handlers.USBkm232Handler(servo, self._usbkm232)
    else:
      # The following boards don't use Chrome EC.
      if board in ('alex', 'butterfly', 'lumpy', 'zgb'):
        return keyboard_handlers.MatrixKeyboardHandler(servo)
      return keyboard_handlers.ChromeECHandler(servo)

  def close(self):
    """Servod turn down logic."""
    for i, interface in enumerate(self._interface_list):
      self._logger.info('Turning down interface %d' % i)
      if hasattr(interface, 'close'):
        interface.close()

  def _init_ftdi_dummy(self, vendor, product, serialname, interface):
    """Dummy interface for ftdi devices.

    This is a dummy function specifically for ftdi devices to not initialize
    anything but to help pad the interface list.

    Returns:
      None.
    """
    return None

  def _init_ftdi_gpio(self, vendor, product, serialname, interface):
    """Initialize gpio driver interface and open for use.

    Args:
      interface: interface number of FTDI device to use.

    Returns:
      Instance object of interface.

    Raises:
      ServodError: If init fails
    """
    fobj = ftdigpio.Fgpio(vendor, product, interface, serialname)
    try:
      fobj.open()
    except ftdigpio.FgpioError as e:
      raise ServodError('Opening gpio interface. %s ( %d )' % (e.msg, e.value))

    return fobj

  def _init_stm32_uart(self, vendor, product, serialname, interface):
    """Initialize stm32 uart interface and open for use

    Note, the uart runs in a separate thread.  Users wishing to
    interact with it will query control for the pty's pathname and connect
    with their favorite console program.  For example:
      cu -l /dev/pts/22

    Args:
      interface: dict of interface parameters.

    Returns:
      Instance object of interface

    Raises:
      ServodError: Raised on init failure.
    """
    self._logger.info('Suart: interface: %s' % interface)
    sobj = stm32uart.Suart(vendor, product, interface['interface'], serialname)

    try:
      sobj.run()
    except stm32uart.SuartError as e:
      raise ServodError('Running uart interface. %s ( %d )' % (e.msg, e.value))

    self._logger.info('%s' % sobj.get_pty())
    return sobj

  def _init_stm32_gpio(self, vendor, product, serialname, interface):
    """Initialize stm32 gpio interface.
    Args:
      interface: dict of interface parameters.

    Returns:
      Instance object of interface

    Raises:
      SgpioError: Raised on init failure.
    """
    interface_number = interface
    # Interface could be a dict.
    if type(interface) is dict:
      interface_number = interface['interface']
    self._logger.info('Sgpio: interface: %s' % interface_number)
    return stm32gpio.Sgpio(vendor, product, interface_number, serialname)

  def _init_stm32_i2c(self, vendor, product, serialname, interface):
    """Initialize stm32 USB to I2C bridge interface and open for use

    Args:
      interface: dict of interface parameters.

    Returns:
      Instance object of interface.

    Raises:
      Si2cError: Raised on init failure.
    """
    self._logger.info('Si2cBus: interface: %s' % interface)
    port = interface.get('port', 0)
    return stm32i2c.Si2cBus(vendor, product, interface['interface'], port=port,
                            serialname=serialname)

  def _init_bb_adc(self, vendor, product, serialname, interface):
    """Initalize beaglebone ADC interface."""
    return bbadc.BBadc()

  def _init_bb_gpio(self, vendor, product, serialname, interface):
    """Initalize beaglebone gpio interface."""
    return bbgpio.BBgpio()

  def _init_ftdi_i2c(self, vendor, product, serialname, interface):
    """Initialize i2c interface and open for use.

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance object of interface

    Raises:
      ServodError: If init fails
    """
    fobj = ftdii2c.Fi2c(vendor, product, interface, serialname)
    try:
      fobj.open()
    except ftdii2c.Fi2cError as e:
      raise ServodError('Opening i2c interface. %s ( %d )' % (e.msg, e.value))

    # Set the frequency of operation of the i2c bus.
    # TODO(tbroch) make configureable
    fobj.setclock(MAX_I2C_CLOCK_HZ)

    return fobj

  # TODO (sbasi) crbug.com/187489 - Implement bb_i2c.
  def _init_bb_i2c(self, interface):
    """Initalize beaglebone i2c interface."""
    return bbi2c.BBi2c(interface)

  def _init_dev_i2c(self, vendor, product, serialname, interface):
    """Initalize Linux i2c-dev interface."""
    return i2cbus.I2CBus('/dev/i2c-%d' % interface['bus_num'])

  def _init_ftdi_uart(self, vendor, product, serialname, interface):
    """Initialize ftdi uart inteface and open for use

    Note, the uart runs in a separate thread (pthreads).  Users wishing to
    interact with it will query control for the pty's pathname and connect
    with there favorite console program.  For example:
      cu -l /dev/pts/22

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance object of interface

    Raises:
      ServodError: If init fails
    """
    fobj = ftdiuart.Fuart(vendor, product, interface, serialname)
    try:
      fobj.run()
    except ftdiuart.FuartError as e:
      raise ServodError('Running uart interface. %s ( %d )' % (e.msg, e.value))

    self._logger.info('%s' % fobj.get_pty())
    return fobj

  # TODO (sbasi) crbug.com/187492 - Implement bbuart.
  def _init_bb_uart(self, vendor, product, serialname, interface):
    """Initalize beaglebone uart interface."""
    logging.debug('UART INTERFACE: %s', interface)
    return bbuart.BBuart(interface)

  def _init_ftdi_gpiouart(self, vendor, product, serialname, interface):
    """Initialize special gpio + uart interface and open for use

    Note, the uart runs in a separate thread (pthreads).  Users wishing to
    interact with it will query control for the pty's pathname and connect
    with there favorite console program.  For example:
      cu -l /dev/pts/22

    Args:
      interface: interface number of FTDI device to use

    Returns:
      Instance objects of interface

    Raises:
      ServodError: If init fails
    """
    fgpio = self._init_ftdi_gpio(vendor, product, serialname, interface)
    fuart = ftdiuart.Fuart(vendor, product, interface, serialname, fgpio._fc)
    try:
      fuart.run()
    except ftdiuart.FuartError as e:
      raise ServodError('Running uart interface. %s ( %d )' % (e.msg, e.value))

    self._logger.info('uart pty: %s' % fuart.get_pty())
    return fgpio, fuart

  def _init_ec3po_uart(self, vendor, product, serialname, interface):
    """Initialize EC-3PO console interpreter interface.

    Args:
      interface: A dictionary representing the interface.

    Returns:
      An EC3PO object representing the EC-3PO interface or None if there's no
      interface for the USB PD UART.
    """
    raw_uart_name = interface['raw_pty']
    raw_uart_source = interface['source']
    if self._syscfg.is_control(raw_uart_name):
      raw_ec_uart = self.get(raw_uart_name)
      return ec3po_interface.EC3PO(raw_ec_uart, raw_uart_source)
    else:
      # The overlay doesn't have the raw PTY defined, therefore we can skip
      # initializing this interface since no control relies on it.
      self._logger.debug(
          'Skip initializing EC3PO for %s, no control specified.',
          raw_uart_name)
      return None

  def _camel_case(self, string):
    output = ''
    for s in string.split('_'):
      if output:
        output += s.capitalize()
      else:
        output = s
    return output

  def clear_cached_drv(self):
    """Clear the cached drivers.

    The drivers are cached in the Dict _drv_dict when a control is got or set.
    When the servo interfaces are relocated, the cached values may become wrong.
    Should call this method to clear the cached values.
    """
    self._drv_dict = {}

  def _get_param_drv(self, control_name, is_get=True):
    """Get access to driver for a given control.

    Note, some controls have different parameter dictionaries for 'getting' the
    control's value versus 'setting' it.  Boolean is_get distinguishes which is
    being requested.

    Args:
      control_name: string name of control
      is_get: boolean to determine

    Returns:
      tuple (param, drv) where:
        param: param dictionary for control
        drv: instance object of driver for particular control

    Raises:
      ServodError: Error occurred while examining params dict
    """
    self._logger.debug('')
    # if already setup just return tuple from driver dict
    if control_name in self._drv_dict:
      if is_get and ('get' in self._drv_dict[control_name]):
        return self._drv_dict[control_name]['get']
      if not is_get and ('set' in self._drv_dict[control_name]):
        return self._drv_dict[control_name]['set']

    params = self._syscfg.lookup_control_params(control_name, is_get)
    if 'drv' not in params:
      self._logger.error('Unable to determine driver for %s' % control_name)
      raise ServodError("'drv' key not found in params dict")
    if 'interface' not in params:
      self._logger.error('Unable to determine interface for %s' % control_name)
      raise ServodError("'interface' key not found in params dict")

    # Find the candidate servos.  Using servo_v4 with a servo_micro connected as
    # an example, the following shows the priority for selecting the interface.
    #
    # 1. The full name. (e.g. - 'servo_v4_with_servo_micro_interface')
    # 2. servo_micro_interface
    # 3. servo_v4_interface
    # 4. Fallback to the default, interface.
    candidates = [self._version]
    candidates.extend(reversed(self._version.split('_with_')))

    interface_id = 'unknown'
    for c in candidates:
      interface_name = '%s_interface' % c
      if interface_name in params:
        interface_id = params[interface_name]
        self._logger.debug('Using %s parameter.' % interface_name)
        break

    # Use the default interface value if we couldn't find a more specific
    # interface.
    if interface_id == 'unknown':
      interface_id = params['interface']
      self._logger.debug('Using default interface parameter.')

    if interface_id == 'servo':
      interface = self
    else:
      index = int(interface_id)
      interface = self._interface_list[index]

    drv_name = params['drv']
    drv_module = getattr(servo_drv, drv_name)
    drv_class = getattr(drv_module, self._camel_case(drv_name))
    drv = drv_class(interface, params)
    if control_name not in self._drv_dict:
      self._drv_dict[control_name] = {}
    if is_get:
      self._drv_dict[control_name]['get'] = (params, drv)
    else:
      self._drv_dict[control_name]['set'] = (params, drv)
    return (params, drv)

  def doc_all(self):
    """Return all documenation for controls.

    Returns:
      string of <doc> text in config file (xml) and the params dictionary for
      all controls.

      For example:
      warm_reset             :: Reset the device warmly
      ------------------------> {'interface': '1', 'map': 'onoff_i', ... }
    """
    return self._syscfg.display_config()

  def doc(self, name):
    """Retreive doc string in system config file for given control name.

    Args:
      name: name string of control to get doc string

    Returns:
      doc string of name

    Raises:
      NameError: if fails to locate control
    """
    self._logger.debug('name(%s)' % (name))
    if self._syscfg.is_control(name):
      return self._syscfg.get_control_docstring(name)
    else:
      raise NameError('No control %s' % name)

  def safe_switch_usbkey_power(self, power_state, _=None):
    """Toggle the usb power safely.

    Args:
      power_state: The setting to set for the usbkey power.
      _: to conform to current API

    Returns:
      An empty string to appease the xmlrpc gods.
    """
    self.set('image_usbkey_pwr', power_state)
    return ''

  def safe_switch_usbkey(self, mux_direction, _=0):
    """Toggle the usb direction safely.

    Args:
      mux_direction: "servo_sees_usbkey" or "dut_sees_usbkey".
      _: to conform to current API

    Returns:
      An empty string to appease the xmlrpc gods.
    """
    self.set('image_usbkey_direction', mux_direction)
    return ''

  def probe_host_usb_dev(self, _=0):
    """Probe the USB disk device plugged in the servo from the host side.

    Args:
      _: to conform to current API

    Returns:
      USB disk path if one and only one USB disk path is found, otherwise an
    """
    return self.get('image_usbkey_dev')

  def download_image_to_usb(self, image_path, _=0):
    """Download image and save to the USB device found by probe_host_usb_dev.
    If the image_path is a URL, it will download this url to the USB path;
    otherwise it will simply copy the image_path's contents to the USB path.

    Args:
      image_path: path or url to the recovery image.
      _: to conform to current API

    Returns:
      True|False: True if process completed successfully, False if error
                        occurred.
    """
    try:
      self.set('download_image_to_usb_dev', image_path)
      return True
    except Exception:
      return False

  def make_image_noninteractive(self):
    """Makes the recovery image noninteractive.

    A noninteractive image will reboot automatically after installation
    instead of waiting for the USB device to be removed to initiate a system
    reboot.

    Mounts partition 1 of the image stored on usb_dev and creates a file
    called "non_interactive" so that the image will become noninteractive.

    Returns:
      True|False: True if process completed successfully, False if error
                        occurred.
    """
    try:
      usb_dev = self.get('image_usbkey_dev')
      usb_dev_partition = '%s1' % usb_dev
      self.set('make_usb_dev_image_noninteractive', usb_dev_partition)
      return True
    except Exception:
      return False

  def set_get_all(self, cmds):
    """Set &| get one or more control values.

    Args:
      cmds: list of control[:value] to get or set.

    Returns:
      rv: list of responses from calling get or set methods.
    """
    rv = []
    for cmd in cmds:
      if ':' in cmd:
        (control, value) = cmd.split(':')
        rv.append(self.set(control, value))
      else:
        rv.append(self.get(cmd))
    return rv

  def get_serial_number(self, name):
    """Returns the desired serial number from the serialnames dict.

    Args:
      name: A string which is the key into the _serialnames dictionary.

    Returns:
       A string containing the serial number or "unknown".
    """
    if not name:
      name = 'main'

    try:
      return self._serialnames[name]
    except KeyError:
      self._logger.debug("'%s_serialname' not found!", name)
      return 'unknown'

  def get(self, name):
    """Get control value.

    Args:
      name: name string of control

    Returns:
      Response from calling drv get method.  Value is reformatted based on
      control's dictionary parameters

    Raises:
      HwDriverError: Error occurred while using drv
      ServodError: if interfaces are not available within timeout period
    """
    if not self._ifaces_available.wait(self.INTERFACE_AVAILABILITY_TIMEOUT):
      raise ServodError('Timed out waiting for interfaces to become available.')
    self._logger.debug('name(%s)' % (name))
    # This route is to retrieve serialnames on servo v4, which
    # connects to multiple servo-micros or CCD, like the controls,
    # 'ccd_serialname', 'servo_micro_for_soraka_serialname', etc.
    # TODO(aaboagye): Refactor it.
    if 'serialname' in name:
      return self.get_serial_number(name.split('serialname')[0].strip('_'))

    (param, drv) = self._get_param_drv(name)
    try:
      val = drv.get()
      rd_val = self._syscfg.reformat_val(param, val)
      self._logger.debug('%s = %s' % (name, rd_val))
      return rd_val
    except AttributeError, error:
      self._logger.error('Getting %s: %s' % (name, error))
      raise
    except HwDriverError:
      self._logger.error('Getting %s' % (name))
      raise

  def get_all(self, verbose):
    """Get all controls values.

    Args:
      verbose: Boolean on whether to return doc info as well

    Returns:
      string creating from trying to get all values of all controls.  In case of
      error attempting access to control, response is 'ERR'.
    """
    rsp = []
    for name in self._syscfg.syscfg_dict['control']:
      self._logger.debug('name = %s' % name)
      try:
        value = self.get(name)
      except Exception:
        value = 'ERR'
        pass
      if verbose:
        rsp.append('GET %s = %s :: %s' % (name, value, self.doc(name)))
      else:
        rsp.append('%s:%s' % (name, value))
    return '\n'.join(sorted(rsp))

  def set(self, name, wr_val_str):
    """Set control.

    Args:
      name: name string of control
      wr_val_str: value string to write.  Can be integer, float or a
          alpha-numerical that is mapped to a integer or float.

    Raises:
      HwDriverError: Error occurred while using driver
      ServodError: if interfaces are not available within timeout period
    """
    if not self._ifaces_available.wait(self.INTERFACE_AVAILABILITY_TIMEOUT):
      raise ServodError('Timed out waiting for interfaces to become available.')
    self._logger.debug('name(%s) wr_val(%s)' % (name, wr_val_str))
    (params, drv) = self._get_param_drv(name, False)
    wr_val = self._syscfg.resolve_val(params, wr_val_str)
    try:
      drv.set(wr_val)
    except HwDriverError:
      self._logger.error('Setting %s -> %s' % (name, wr_val_str))
      raise
    # TODO(crbug.com/841097) Figure out why despite allow_none=True for both
    # xmlrpc server & client I still have to return something to appease the
    # marshall/unmarshall
    return True

  def hwinit(self, verbose=False):
    """Initialize all controls.

    These values are part of the system config XML files of the form
    init=<value>.  This command should be used by clients wishing to return the
    servo and DUT its connected to a known good/safe state.

    Note that initialization errors are ignored (as in some cases they could
    be caused by DUT firmware deficiencies). This might need to be fine tuned
    later.

    Args:
      verbose: boolean, if True prints info about control initialized.
        Otherwise prints nothing.

    Returns:
      This function is called across RPC and as such is expected to return
      something unless transferring 'none' across is allowed. Hence adding a
      dummy return value to make things simpler.
    """
    for control_name, value in self._syscfg.hwinit:
      try:
        # Workaround for bug chrome-os-partner:42349. Without this check, the
        # gpio will briefly pulse low if we set it from high to high.
        if self.get(control_name) != value:
          self.set(control_name, value)
        if verbose:
          self._logger.info('Initialized %s to %s', control_name, value)
      except Exception:
        self._logger.exception(
            'Problem initializing %s -> %s', control_name, value)

    # Init keyboard after all the intefaces are up.
    self._keyboard = self._init_keyboard_handler(self, self._board)
    return True

  def echo(self, echo):
    """Dummy echo function for testing/examples.

    Args:
      echo: string to echo back to client
    """
    self._logger.debug('echo(%s)' % (echo))
    return 'ECH0ING: %s' % (echo)

  def get_board(self):
    """Return the board specified at startup, if any."""
    return self._board

  def get_base_board(self):
    """Returns the board name of the base if present.

    Returns:
      A string of the board name, or '' if not present.
    """
    # The value is set in servo_postinit.
    return self._base_board

  def get_version(self):
    """Get servo board version."""
    return self._version

  def power_long_press(self):
    """Simulate a long power button press."""
    # After a long power press, the EC may ignore the next power
    # button press (at least on Alex).  To guarantee that this
    # won't happen, we need to allow the EC one second to
    # collect itself.
    return self.set('power_key', 'long_press')

  def power_normal_press(self):
    """Simulate a normal power button press."""
    return self.set('power_key', 'press')

  def power_short_press(self):
    """Simulate a short power button press."""
    return self.set('power_key', 'short_press')

  def power_key(self, press_secs=''):
    """Simulate a power button press.

    Args:
      press_secs: Time in seconds to simulate the keypress.
    """
    return self.set('power_key', 'press' if press_secs is '' else press_secs)

  def ctrl_d(self, press_secs=''):
    """Simulate Ctrl-d simultaneous button presses."""
    return self.set('ctrl_d', 'tab' if press_secs is '' else press_secs)

  def ctrl_u(self, press_secs=''):
    """Simulate Ctrl-u simultaneous button presses."""
    return self.set('ctrl_u', 'tab' if press_secs is '' else press_secs)

  def ctrl_enter(self, press_secs=''):
    """Simulate Ctrl-enter simultaneous button presses."""
    return self.set('ctrl_enter', 'tab' if press_secs is '' else press_secs)

  def d_key(self, press_secs=''):
    """Simulate Enter key button press."""
    return self.set('d_key', 'tab' if press_secs is '' else press_secs)

  def ctrl_key(self, press_secs=''):
    """Simulate Enter key button press."""
    return self.set('ctrl_key', 'tab' if press_secs is '' else press_secs)

  def enter_key(self, press_secs=''):
    """Simulate Enter key button press."""
    return self.set('enter_key', 'tab' if press_secs is '' else press_secs)

  def refresh_key(self, press_secs=''):
    """Simulate Refresh key (F3) button press."""
    return self.set('refresh_key', 'tab' if press_secs is '' else press_secs)

  def ctrl_refresh_key(self, press_secs=''):
    """Simulate Ctrl and Refresh (F3) simultaneous press.

    This key combination is an alternative of Space key.
    """
    return self.set('ctrl_refresh_key', ('tab' if press_secs is '' else
                                         press_secs))

  def imaginary_key(self, press_secs=''):
    """Simulate imaginary key button press.

    Maps to a key that doesn't physically exist.
    """
    return self.set('imaginary_key', 'tab' if press_secs is '' else press_secs)

  def sysrq_x(self, press_secs=''):
    """Simulate Alt VolumeUp X simultaneous press.

    This key combination is the kernel system request (sysrq) x.
    """
    return self.set('sysrq_x', 'tab' if press_secs is '' else press_secs)

  def get_servo_serials(self):
    """Return all the serials associated with this process."""
    return self._serialnames


def test():
  """Integration testing.

  TODO(tbroch) Enhance integration test and add unittest (see mox)
  """
  logging.basicConfig(
      level=logging.DEBUG,
      format='%(asctime)s - %(name)s - ' + '%(levelname)s - %(message)s')
  # configure server & listen
  servod_obj = Servod(1)
  # 5 == number of interfaces on a FT4232H device
  for i in xrange(1, 5):
    if i == 2:
      # its an i2c interface ... see __init__ for details and TODO to make
      # this configureable
      servod_obj._interface_list[i].wr_rd(0x21, [0], 1)
    else:
      # its a gpio interface
      servod_obj._interface_list[i].wr_rd(0)

  server = SimpleXMLRPCServer.SimpleXMLRPCServer(('localhost', 9999),
                                                 allow_none=True)
  server.register_introspection_functions()
  server.register_multicall_functions()
  server.register_instance(servod_obj)
  logging.info('Listening on localhost port 9999')
  server.serve_forever()


if __name__ == '__main__':
  test()

  # simple client transaction would look like
  """remote_uri = 'http://localhost:9999' client = xmlrpclib.ServerProxy(remote_uri, verbose=False) send_str = "Hello_there" print "Sent " + send_str + ", Recv " + client.echo(send_str)

  """
