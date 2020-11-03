# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo Server."""
import logging
import os
import re
try:
  from SimpleXMLRPCServer import SimpleXMLRPCServer
except ImportError:
  from xmlrpc.server import SimpleXMLRPCServer
  # TODO(crbug.com/999878): This is for python3 compatibility.
  # Remove once fully moved to python3.
import time
import usb
import weakref

import drv as servo_drv
import interface as _interface
import servo_dev
import servo_interfaces
import servo_logging
import servo_postinit

HwDriverError = servo_drv.hw_driver.HwDriverError


class ServodError(Exception):
  """Exception class for servod."""


class Servod(object):
  """Main class for Servo debug/controller Daemon."""

  # This is the key to get the main serial used in the _serialnames dict.
  MAIN_SERIAL = 'main'
  SERVO_MICRO_SERIAL = 'servo_micro'
  C2D2_SERIAL = 'c2d2'
  CCD_SERIAL = 'ccd'

  # Timeout to wait for interfaces to become available again if reinitialization
  # is taking place. In seconds. This is supposed to recover from brief resets.
  # If the interface disappears for more than 5 seconds, then someone probably
  # intentionally disconnected the device. Servod shouldn't be responsible for
  # waiting for the device during an intentional disconnect.
  INTERFACE_AVAILABILITY_TIMEOUT = 5

  # Exceptions to count as known or ordinary.  Any errors that aren't instances
  # of these (or their subclasses) will be logged with "Please take a look."
  KNOWN_EXCEPTIONS = (AttributeError, NameError, HwDriverError)

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
    self.add_device(device)

    # Extend the interface list if we need to.
    interfaces_len = len(interfaces)
    interface_list_len = len(self._interface_list)
    if interfaces_len > interface_list_len:
      # Fill with dummies.
      self._interface_list += [_interface.empty.Empty()] * (interfaces_len -
                                                            interface_list_len)

    for i, interface_data in enumerate(interfaces):
      if type(interface_data) is dict:
        name = interface_data['name']
        # Store interface index for those that care about it.
        interface_data['index'] = i
      elif type(interface_data) is str:
        if interface_data in ['empty', 'ftdi_empty']:
          # 'empty' reserves the interface for future use.  Typically the
          # interface will be managed by external third-party tools like
          # openOCD for JTAG or flashrom for SPI.  In the case of servo V4,
          # it serves as a placeholder for servo micro interfaces.
          continue
        name = interface_data
      else:
        raise ServodError('Illegal interface data type %s'
                          % type(interface_data))

      self._logger.info('Initializing interface %d to %s', i, name)
      result = _interface.Build(name=name, index=i, vid=vendor, pid=product,
                                sid=serialname, interface_data=interface_data,
                                servod=self)
      if isinstance(result, tuple):
        result_len = len(result)
        self._interface_list[i:(i + result_len)] = result
      else:
        self._interface_list[i] = result

  def __init__(self, config, vendor, product, serialname=None, interfaces=None,
               board='', model='', version=None, usbkm232=None):
    """Servod constructor.

    Args:
      config: instance of SystemConfig containing all controls for
          particular Servod invocation
      vendor: usb vendor id of FTDI device
      product: usb product id of FTDI device
      serialname: string of device serialname/number as defined in FTDI eeprom.
      interfaces: list of strings of interface types the server will instantiate
      board: board name. e.g. octopus, coral, or scarlet.
      model: model name of a given board. e.g. fleex, ampton, or apel.
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
    self._vendor = vendor
    self._product = product
    self._devices = {}
    self._serialnames = {self.MAIN_SERIAL: serialname}
    self._syscfg = config
    # list of objects (Fi2c, Fgpio) to physical interfaces (gpio, i2c) that ftdi
    # interfaces are mapped to
    self._interface_list = []
    # Dict of Dict to map control name, function name to to tuple (params, drv)
    # Ex) _drv_dict[name]['get'] = (params, drv)
    self._drv_dict = {}
    self._base_board = ''
    self._board = board
    if model:
      self._board += '_' + model
    self._model = model
    self._version = version
    self._usbkm232 = usbkm232
    self._keyboard = None
    self._usb_keyboard = None
    if not interfaces:
      try:
        interfaces = servo_interfaces.INTERFACE_BOARDS[board][vendor][product]
      except KeyError:
        interfaces = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]
    self._interfaces = interfaces

    self.init_servo_interfaces(vendor, product, serialname, interfaces)
    servo_postinit.post_init(self)
    self._syscfg.finalize()

  def reinitialize(self):
    """Reinitialize all interfaces that support reinitialization"""
    for i, interface in enumerate(self._interface_list):
      interface.reinitialize()
    # Indicate interfaces are safe to use again.
    for device in self._devices.values():
        device.connect()

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

  def close(self):
    """Servod turn down logic."""
    for i, interface in enumerate(self._interface_list):
      self._logger.info('Turning down interface %d' % i)
      interface.close()

  def get_devices(self):
    return self._devices.values()

  def add_device(self, device):
    if device not in self._devices:
      vid, pid, serial = device
      servod_device = servo_dev.ServoDevice(vid, pid, serial)
      self._devices[device] = servod_device

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

  def _get_servo_specific_param(self, params, param_key, control_name):
    """Get |param_key| from params by looking for servo specific params first.

    Find the candidate servos.  Using servo_v4 with a servo_micro connected as
    example, the following shows the priority for selecting the interface.

    1. The full name. (e.g. - 'servo_v4_with_servo_micro_interface')
    2. servo_micro_interface
    3. servo_v4_interface
    4. Fallback to the default, interface.

    Args:
      params: params dictionary for a control
      param_key: identifier in the params dictionary to look for
      control_name: control name the params correspond to

    Returns:
      The best suited param value for param_key given the servo type or
      None if even the default is not defined.
    """
    candidates = [self._version]
    if '_with_' in self._version:
      v4, raw_dut_device = self._version.split('_with_')
      dut_devices = raw_dut_device.split('_and_')
      # NOTE(coconutruben): all of this nonsense is going away with the new
      # servod and is to bridge the time until then. Please forgive the below
      # until then.
      if '.' in control_name:
        # In the current implementation, the only case where a '.' (a prefix)
        # is in the control name is when there is a dual instance with micro and
        # ccd on a v4.
        dut_device = dut_devices[1]
      else:
        # In the normal control name, we need to make sure the version used
        # does not include the potential _and_ portion from a dual instance.
        dut_device = dut_devices[0]
      candidates.extend([dut_device, v4])
    candidates = ['%s_%s' % (c, param_key) for c in candidates]
    candidates.append(param_key)
    for c in candidates:
      if c in params:
        self._logger.debug('Using %s parameter.', c)
        return params[c]
    self._logger.error('Unable to determine %s for %s', param_key, control_name)
    self._logger.error('params: %r', params)
    return None

  def _get_param_drv(self, control_name, is_get=True):
    """Get access to driver for a given control.

    Note, some controls have different parameter dictionaries for 'getting' the
    control's value versus 'setting' it.  Boolean is_get distinguishes which is
    being requested.

    Args:
      control_name: string name of control
      is_get: boolean to determine

    Returns:
      tuple (params, drv, device_info) where:
        params: param dictionary for control
        drv: instance object of driver for particular control
        device_info: servo device information

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

    # Get the most suitable drv given the servo instance.
    drv_name = self._get_servo_specific_param(params, 'drv', control_name)
    if drv_name == 'na':
      # 'na' drv can be used to selectively turn controls into noops for
      # a given servo hardware. Ensure that there is an interface.
      params.setdefault('interface', 'servo')
      self._logger.debug('Setting interface to default to %r for %r unless '
                         ' defined  in params, as drv is %r.', 'servo',
                         control_name, 'na')
      # Setting input_type to str allows all inputs through enabling a true noop
      params.update({'input_type': 'str'})
    interface_id = self._get_servo_specific_param(params, 'interface',
                                                  control_name)
    if None in [drv_name, interface_id]:
      raise ServodError('No drv/interface for control %r found' % control_name)

    if interface_id == 'servo':
      interface = weakref.proxy(self)
    else:
      index = int(interface_id)
      interface = self._interface_list[index]

    device_info = None
    if hasattr(interface, 'get_device_info'):
      device_info = interface.get_device_info()
    drv_module = getattr(servo_drv, drv_name)
    drv_class = getattr(drv_module, self._camel_case(drv_name))
    drv = drv_class(interface, params)
    if control_name not in self._drv_dict:
      self._drv_dict[control_name] = {}
    if is_get:
      self._drv_dict[control_name]['get'] = (params, drv, device_info)
    else:
      self._drv_dict[control_name]['set'] = (params, drv, device_info)
    return (params, drv, device_info)

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
        (control, value) = cmd.split(':', 1)
        rv.append(self.set(control, value))
      else:
        rv.append(self.get(cmd))
    return rv

  def add_serial_number(self, name, serial_number):
    """Adds the serial number to the _serialnames dictionary.

    Args:
      name: A string which is the key into the _serialnames dictionary.
      serial_number: A string which is the key into the _serialnames dictionary.
    """
    self._serialnames[name] = serial_number
    self._logger.debug('Added %s %s to serialnames %r', name, serial_number,
                       self._serialnames)

  def get_serial_number(self, name):
    """Returns the desired serial number from the serialnames dict.

    Args:
      name: A string which is the key into the _serialnames dictionary.

    Returns:
       A string containing the serial number or "unknown".
    """
    # Remove the prefix from the serialname control. Serialnames are
    # universal. It doesn't matter what the prefix is.
    # The prefix is separated from the main control with '.'
    name = name.split('.', 1)[-1]

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
    if 'serialname' in name:
      # This route is to retrieve serialnames on servo v4, which
      # connects to multiple servo-micros or CCD, like the controls,
      # 'ccd_serialname', 'servo_micro_for_soraka_serialname', etc.
      # TODO(aaboagye): Refactor it.
      return self.get_serial_number(name.split('serialname')[0].strip('_'))

    with servo_logging.WrapGetCall(
            name, known_exceptions=self.KNOWN_EXCEPTIONS) as wrapper:
      (params, drv, device) = self._get_param_drv(name)
      if device in self._devices:
        self._devices[device].wait(self.INTERFACE_AVAILABILITY_TIMEOUT)

      val = drv.get()
      rd_val = self._syscfg.reformat_val(params, val)
      wrapper.got_result(rd_val)
      return rd_val

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
    with servo_logging.WrapSetCall(
            name, wr_val_str, known_exceptions=self.KNOWN_EXCEPTIONS):
      (params, drv, device) = self._get_param_drv(name, False)
      if device in self._devices:
        self._devices[device].wait(self.INTERFACE_AVAILABILITY_TIMEOUT)
      wr_val = self._syscfg.resolve_val(params, wr_val_str)

      drv.set(wr_val)

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
      mock return value to make things simpler.
    """
    for control_name, value in self._syscfg.hwinit:
      try:
        # Workaround for bug chrome-os-partner:42349. Without this check, the
        # gpio will briefly pulse low if we set it from high to high.
        if self.get(control_name) != value:
          self.set(control_name, value)
        if verbose:
          self._logger.info('Initialized %s to %s', control_name, value)
      except Exception as e:
        self._logger.error(
            'Problem initializing %s -> %s', control_name, value)
        self._logger.error(str(e))
        self._logger.error('Please consider verifying the logs and if the '
                           'error is not just a setup issue, consider filing '
                           'a bug. Also checkout go/servo-ki.')

    # If there is the control of 'active_v4_device', set active_v4_device to
    # the default device as initialization.
    try:
      if self._syscfg.is_control('active_v4_device'):
        self.set('active_v4_device', 'default')
    except servo_drv.active_v4_device.activeV4DeviceError as e:
      self._logger.debug('Could not set active device: %s', str(e))

    return True

  def echo(self, echo):
    """Mock echo function for testing/examples.

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
  for i in range(1, 5):
    if i == 2:
      # its an i2c interface ... see __init__ for details and TODO to make
      # this configureable
      servod_obj._interface_list[i].wr_rd(0x21, [0], 1)
    else:
      # its a gpio interface
      servod_obj._interface_list[i].wr_rd(0)

  server = SimpleXMLRPCServer(('localhost', 9999), allow_none=True)
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
