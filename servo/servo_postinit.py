# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Specific Servo PostInit functions."""

import collections
import copy
import logging
import os
import re
import subprocess
import time
import usb

import recovery
import servo_interfaces
import system_config
import utils.diagnose
import utils.usb_hierarchy as usb_hierarchy

POST_INIT = collections.defaultdict(dict)

DUAL_V4_VAR = 'DUAL_V4_CFG'
DUAL_V4_VAR_EMPTY = 'empty'


ServoType = collections.namedtuple('ServoType', [
    # str - String to use in servod DUT control names.
    'control_prefix',
    # str - Servo controls config file name (not full path).
    'cfg_file_name',
    # str - Key for Servod serial name dict.
    'serial_key',
    # [(int, int)] - List of USB VID + PID pairs.
    'vid_pid_pairs',
])


DEBUG_HEADER_SERVO_TYPES = [
    ServoType(
        control_prefix='servo_micro',
        cfg_file_name='servo_micro.xml',
        serial_key='servo_micro',
        vid_pid_pairs=servo_interfaces.SERVO_MICRO_DEFAULTS,
    ),
    ServoType(
        control_prefix='c2d2',
        cfg_file_name='c2d2.xml',
        serial_key='c2d2',
        vid_pid_pairs=servo_interfaces.C2D2_DEFAULTS,
    ),
]


CCD_SERVO_TYPES = [
    ServoType(
        control_prefix='ccd_cr50',
        cfg_file_name='ccd_cr50.xml',
        serial_key='ccd',
        vid_pid_pairs=servo_interfaces.CCD_DEFAULTS,
    ),
]


class ServoPostInitError(Exception):
  """Exception class for ServoPostInit."""


class BasePostInit(object):
  """Base Class for Post Init classes."""

  def __init__(self, servod):
    self.servod = servod
    self._logger = logging.getLogger(self.__class__.__name__)

  def post_init(self):
    """Main entry to the post init class, must be implemented by subclasses."""
    raise NotImplementedError('post_init not implemented')


class ServoV4PostInit(BasePostInit):
  """Servo v4 Post init class.

  We're going to check if there are any dut interfaces attached and if they are
  connected through the specific servo v4 initialized in the servod object.  If
  so, we're going to initialize the dut interfaces connected to the v4 so that
  the user can control the servo v4 and dut interfaces through one servod
  process.
  """

  # TODO(b/154436412): Support servo_v4p1.
  def get_servo_v4_usb_device(self):
    """Return associated servo v4 usb.core.Device object.

    Returns:
      servo v4 usb.core.Device object associated with the servod instance.
    """
    servo_v4_candidates = usb_hierarchy.Hierarchy.GetAllUsbDevices(
        servo_interfaces.SERVO_V4_DEFAULTS)
    for d in servo_v4_candidates:
      d_serial = usb.util.get_string(d, d.iSerialNumber)
      if (not self.servod.get_serial_number(self.servod.MAIN_SERIAL) or
          d_serial == self.servod.get_serial_number(self.servod.MAIN_SERIAL)):
        return d
    return None

  def prepend_config(self, new_cfg_file, remove_head=False, name_prefix=None,
                     interface_increment=0):
    """Prepend the given new config file to the existing system config.

    The new config, like servo_micro, is properly overwritten by some board
    overlays. So we will recreate the config list but with the new config
    in front and append the rest of the existing config files loaded
    up. Duplicates are ok since the SystemConfig object keeps track of that
    for us and will ignore them.

    Args:
      new_cfg_file: List of config files.
      remove_head: True to remove the head of the existing loaded config files.
      name_prefix: string to prepend to all control names
      interface_increment: number to add to all interfaces
    """
    cfg_files = [(new_cfg_file, name_prefix, interface_increment)]
    first_index = 1 if remove_head else 0
    cfg_files.extend(self.servod._syscfg._loaded_xml_files[first_index:])

    self._logger.debug('Resetting system config files')
    new_syscfg = system_config.SystemConfig()
    for cfg_file in cfg_files:
      new_syscfg.add_cfg_file(*cfg_file)
    self.servod._syscfg = new_syscfg

  def add_servo_serial(self, servo_usb, servo_serial_key):
    """Add the servo serial number.

    Args:
      servo_usb: usb.core.Device object that represents the new detected
          servo we should be checking against.
      servo_serial_key: Key to the servo serial dict.
    """
    serial = usb.util.get_string(servo_usb, servo_usb.iSerialNumber)
    self.servod.add_serial_number(servo_serial_key, serial)

  def init_servo_interfaces(self, servo_usb, servo_interface=None):
    """Initialize the new servo interfaces.

    Args:
      servo_usb: usb.core.Device object that represents the new detected
          servo we should be checking against.
      servo_interface: list of interfaces to init. If not provided, the default
                       for vid/pid will be used.
    """
    vendor = servo_usb.idVendor
    product = servo_usb.idProduct
    serial = usb.util.get_string(servo_usb, servo_usb.iSerialNumber)
    if not servo_interface:
      servo_interface = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]

    self.servod.init_servo_interfaces(vendor, product, serial, servo_interface)

  def probe_ec_board(self):
    """Probe the ec board behind the servo, and check if it needs relocation.

    Returns:
      The board name if it needs relocation; otherwise, None.
    """
    try:
      self.servod.set('ec_uart_en', 'on')
      board = self.servod.get('ec_board')
      self._logger.info('Detected board: %s', board)
    except:
      self._logger.error('Failed to query EC board name')
      return None

    if board in servo_interfaces.SERVO_V4_SLOT_POSITIONS:
      return board
    else:
      return None

  def kick_devices(self):
    """General method to do misc actions.

    We'll need to do certain things (like 'lsusb' for servo micro) to ensure
    we can detect and initialize extra devices properly.  This method is here
    to hold all those necessary pre-postinit actions.
    """
    # Run 'lsusb' so that servo micros are configured and show up in sysfs.
    subprocess.call(['lsusb'])

  def post_init(self):
    self._logger.debug('')

    # Do misc actions so we can detect devices we might want to initialize.
    self.kick_devices()

    # Snapshot the USB hierarchy at this moment.
    hierarchy = usb_hierarchy.Hierarchy()

    found_debug_header_servo = False
    # We want to check if we have one/multiple servo micros connected to
    # this servo v4 and if so, initialize it and add it to the servod instance.
    servo_v4 = self.get_servo_v4_usb_device()
    # Save the board config in case we need to readd it with a prefix.
    board_config = self.servod._syscfg.get_board_cfg()

    # Find debug header servos, e.g. Servo Micro, C2D2.
    for servo_type in DEBUG_HEADER_SERVO_TYPES:
      for servo_usb_device in usb_hierarchy.Hierarchy.GetAllUsbDevices(
          servo_type.vid_pid_pairs):
        # The servo_micro/C2D2 and the STM chip of servo v4 share the same
        # internal hub on servo v4 board. Check the USB hierarchy to find the
        # servo_micro/C2D2 behind.
        if hierarchy.DevOnDevHub(servo_v4, servo_usb_device):
          default_slot = servo_interfaces.SERVO_V4_SLOT_POSITIONS['default']
          slot_size = servo_interfaces.SERVO_V4_SLOT_SIZE
          backup_interfaces = self.servod.get_servo_interfaces(
              default_slot, slot_size)

          self.prepend_config(servo_type.cfg_file_name)
          self.init_servo_interfaces(servo_usb_device)
          # Interfaces change; clear the cached.
          self.servod.clear_cached_drv()

          board = self.probe_ec_board()
          if board:
            # Assume only one base connected
            if not self.servod._base_board:
              self.servod._base_board = board
            else:
              raise ServoPostInitError('More than one base connected.')

            new_slot = servo_interfaces.SERVO_V4_SLOT_POSITIONS[board]
            self._logger.info('EC board requiring relocation: %s', board)
            self._logger.info('Move the servo interfaces from %d to %d',
                              default_slot, new_slot)
            self.servod.set_servo_interfaces(new_slot,
                                             self.servod.get_servo_interfaces(
                                                 default_slot, slot_size))
            # Restore the original interfaces.
            self.servod.set_servo_interfaces(default_slot, backup_interfaces)
            # Interfaces change; clear the cached.
            self.servod.clear_cached_drv()

            # Load the config with modified control names and interface ids.
            self.prepend_config(servo_interfaces.SERVO_V4_CONFIGS[board], True,
                                '%s_' % board, new_slot - 1)

            # Add its serial for record.
            self.add_servo_serial(
                servo_usb_device, servo_type.serial_key + '_for_' + board)
          else:
            # Append "_with_servo_micro" or "_with_c2d2" to the version string.
            # Don't do it on a base, as the base is optional.
            self.servod._version += '_with_' + servo_type.control_prefix
            # This is the main servo_micro/c2d2.
            self.add_servo_serial(servo_usb_device, servo_type.serial_key)
            # Add aliases for the servo_micro/c2d2 as well.  This is useful if
            # there are multiple debug header servos.
            if self.servod._board:
              self.add_servo_serial(
                  servo_usb_device,
                  servo_type.serial_key + '_for_' + self.servod._board)
              if self.servod._model:
                self.add_servo_serial(
                    servo_usb_device,
                    servo_type.serial_key + '_for_' + self.servod._model)
            found_debug_header_servo = True

    if found_debug_header_servo and not DUAL_V4_VAR in os.environ:
      return

    # Flag to determine whether a main device has been found,
    # ccd or servo_micro or c2d2.
    found_dut_controller = found_debug_header_servo

    # Find Case-Closed Debug (CCD) Servos, e.g. CR50.
    for servo_type in CCD_SERVO_TYPES:
      for ccd_usb_device in usb_hierarchy.Hierarchy.GetAllUsbDevices(
          servo_type.vid_pid_pairs):
        # Pick the proper CCD endpoint behind the servo v4.
        if hierarchy.DevOnDevHub(servo_v4, ccd_usb_device):
          if not found_debug_header_servo:
            self.prepend_config(servo_type.cfg_file_name)
            self.servod._version += '_with_' + servo_type.control_prefix
            self.init_servo_interfaces(ccd_usb_device)
            found_dut_controller = True
          else:
            ccd_prefix = servo_type.control_prefix + '.'
            ccd_pos = servo_interfaces.SERVO_V4_SLOT_POSITIONS['secondary_ccd']
            ccd_shift = ccd_pos - 1
            # Cache the previous hwinit, ccd controls should not be hwinit.
            cached_hwinit = copy.copy(self.servod._syscfg.hwinit)
            self.servod._syscfg.add_cfg_file(servo_type.cfg_file_name,
                                             interface_increment=ccd_shift,
                                             name_prefix=ccd_prefix)
            if board_config:
              self.servod._syscfg.add_cfg_file(board_config,
                                               interface_increment=ccd_shift,
                                               name_prefix=ccd_prefix)

            self.servod._syscfg.hwinit = cached_hwinit
            vid, pid = (ccd_usb_device.idVendor, ccd_usb_device.idProduct)
            interfaces = servo_interfaces.INTERFACE_DEFAULTS[vid][pid]
            for interface in interfaces:
              # Rewrite the ec3po interfaces to use the prefix for the raw uart.
              if isinstance(interface, dict) and 'raw_pty' in interface:
                interface['raw_pty'] = ccd_prefix + interface['raw_pty']
            # Need to shift the interfaces properly.
            interfaces = ['empty'] * ccd_shift + interfaces
            self.servod._version += '_and_' + servo_type.control_prefix
            self.init_servo_interfaces(ccd_usb_device, interfaces)
          self.add_servo_serial(ccd_usb_device, servo_type.serial_key)

    if found_dut_controller:
      return

    # Fail if we requested board control but don't have an interface for this.
    if self.servod._board:
      ccd_capable = self.servod.get('servo_v4_type') == 'type-c'
      if ccd_capable:
        faults = utils.diagnose.diagnose_ccd(self.servod)
        if utils.diagnose.SBU_VOLTAGE_FLOAT in faults:
          self.servod.set('dut_sbu_voltage_float_fault', 'on')
      # No need to check for the LOW voltage signal here as the fault
      # is valid for both ccd and for servo micro: a controller is missing
      self.servod.set('dut_controller_missing_fault', 'on')

      self._logger.error('No Servo Micro, C2D2, or CCD detected for board %s',
          self.servod._board)
      # TODO(guocb): remove below tip when DUTs directionality is stable.
      self._logger.error('Try flipping the USB type C cable if you were using '
                         'servo v4 type C.')
      self._logger.error('If flipping the cable allows CCD, please file a bug '
                         'against the DUT platform with reproducing details.')
      if recovery.is_recovery_active():
        self._logger.info('Will continue startup as recovery mode has '
                          'been requested')
      else:
        raise ServoPostInitError('No device interface '
                                 '(Servo Micro, C2D2, or CCD) connected.')
    else:
      self._logger.info('No Servo Micro / C2D2 and CCD detected.')


# Add in servo v4 post init method.
for vid, pid in servo_interfaces.SERVO_V4_DEFAULTS:
  POST_INIT[vid][pid] = ServoV4PostInit


def post_init(servod):
  """Entry point to call post init for a given vid/pid and servod.

  Args:
    servod: servo_server.Servod object.
  """
  post_init_class = POST_INIT.get(servod._vendor, {}).get(servod._product)
  if post_init_class:
    post_init_class(servod).post_init()
