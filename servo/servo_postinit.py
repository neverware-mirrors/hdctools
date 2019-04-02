# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Specific Servo PostInit functions."""

import collections
import logging
import os
import re
import subprocess
import time
import usb

import servo_interfaces
import servodutil as util
import system_config

POST_INIT = collections.defaultdict(dict)


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

  SERVO_MICRO_CFG = 'servo_micro.xml'
  # Only support CR50 CCD.
  CCD_CFG = 'ccd_cr50.xml'


  def get_servo_v4_usb_device(self):
    """Return associated servo v4 usb.core.Device object.

    Returns:
      servo v4 usb.core.Device object associated with the servod instance.
    """
    servo_v4_candidates = util.UsbHierarchy.GetAllUsbDevices(
        servo_interfaces.SERVO_V4_DEFAULTS)
    for d in servo_v4_candidates:
      d_serial = usb.util.get_string(d, 256, d.iSerialNumber)
      if (not self.servod._serialnames[self.servod.MAIN_SERIAL] or
          d_serial == self.servod._serialnames[self.servod.MAIN_SERIAL]):
        return d
    return None

  def get_servo_micro_devices(self):
    """Return all servo micros detected.

    Returns:
      List of servo micro devices as usb.core.Device objects.
    """
    vid_pid_list = servo_interfaces.SERVO_MICRO_DEFAULTS
    return util.UsbHierarchy.GetAllUsbDevices(vid_pid_list)

  def get_ccd_devices(self):
    """Return all CCD USB devices detected.

    Returns:
      List of CCD USB devices as usb.core.Device objects.
    """
    return util.UsbHierarchy.GetAllUsbDevices(servo_interfaces.CCD_DEFAULTS)

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
    serial = usb.util.get_string(servo_usb, 256, servo_usb.iSerialNumber)
    self.servod._serialnames[servo_serial_key] = serial
    self._logger.debug('servod.serialnames = %r', self.servod._serialnames)

  def init_servo_interfaces(self, servo_usb):
    """Initialize the new servo interfaces.

    Args:
      servo_usb: usb.core.Device object that represents the new detected
          servo we should be checking against.
    """
    vendor = servo_usb.idVendor
    product = servo_usb.idProduct
    serial = usb.util.get_string(servo_usb, 256, servo_usb.iSerialNumber)
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
    usb_hierarchy = util.UsbHierarchy()

    main_micro_found = False
    # We want to check if we have one/multiple servo micros connected to
    # this servo v4 and if so, initialize it and add it to the servod instance.
    servo_v4 = self.get_servo_v4_usb_device()
    servo_micro_candidates = self.get_servo_micro_devices()
    for servo_micro in servo_micro_candidates:
      # The servo_micro and the STM chip of servo v4 share the same internal hub
      # on servo v4 board. Check the USB hierarchy to find the servo_micro
      # behind.
      if usb_hierarchy.ShareSameHub(servo_v4, servo_micro):
        default_slot = servo_interfaces.SERVO_V4_SLOT_POSITIONS['default']
        slot_size = servo_interfaces.SERVO_V4_SLOT_SIZE
        backup_interfaces = self.servod.get_servo_interfaces(
            default_slot, slot_size)

        self.prepend_config(self.SERVO_MICRO_CFG)
        self.init_servo_interfaces(servo_micro)
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
                              board, new_slot - 1)

          # Add its serial for record.
          self.add_servo_serial(
              servo_micro, self.servod.SERVO_MICRO_SERIAL + '_for_' + board)
        else:
          # Append "_with_servo_micro" to the version string. Don't do it on a
          # base, as the base is optional.
          self.servod._version += '_with_servo_micro'
          # This is the main servo-micro.
          self.add_servo_serial(servo_micro, self.servod.SERVO_MICRO_SERIAL)
          # Add aliases for the servo micro as well.  This is useful if there
          # are multiple servo micros.
          self.add_servo_serial(
              servo_micro,
              self.servod.SERVO_MICRO_SERIAL + '_for_' + self.servod._board)
          if self.servod._model:
            self.add_servo_serial(
                servo_micro,
                self.servod.SERVO_MICRO_SERIAL + '_for_' + self.servod._model)
          main_micro_found = True

    if main_micro_found:
      return

    # Try to enable CCD iff no main servo-micro is detected.
    ccd_candidates = self.get_ccd_devices()
    for ccd in ccd_candidates:
      # Pick the proper CCD endpoint behind the servo v4.
      if usb_hierarchy.ShareSameHub(servo_v4, ccd):
        self.prepend_config(self.CCD_CFG)
        self.add_servo_serial(ccd, self.servod.CCD_SERIAL)
        self.init_servo_interfaces(ccd)
        self.servod._version += '_with_ccd_cr50'
        return

    # Fail if we requested board control but don't have an interface for this.
    if self.servod._board:
      if self.servod.get('servo_v4_type') == 'type-c':
        self.diagnose_ccd()


      self._logger.error('No servo micro or CCD detected for board %s',
          self.servod._board)
      # TODO(guocb): remove below tip when DUTs directionality is stable.
      self._logger.error('Try flipping the USB type C cable if you were using '
                         'servo v4 type C.')
      self._logger.error('If flipping the cable allows CCD, please file a bug '
                         'against the DUT platform with reproducing details.')
      raise ServoPostInitError('No device interface '
                               '(servo micro or CCD) connected.')
    else:
      self._logger.info('No servo micro and CCD detected.')

  def diagnose_ccd(self):
    # Voltage levels indicating ~0V or ~3.3V
    NC_LOW = 300
    NC_HIGH = 2800

    # Check ADC values for SBU lines
    sbu1 = int(self.servod.get('servo_v4_sbu1_mv'))
    sbu2 = int(self.servod.get('servo_v4_sbu2_mv'))
    # Check ADC values for CC lines
    dut_cc1 = int(self.servod.get('servo_v4_dut_cc1_mv'))
    dut_cc2 = int(self.servod.get('servo_v4_dut_cc2_mv'))
    chg_cc1 = int(self.servod.get('servo_v4_chg_cc1_mv'))
    chg_cc2 = int(self.servod.get('servo_v4_chg_cc2_mv'))

    # Check SuzyQ routing settings.
    sbu_en = self.servod.get('sbu_mux_enable') == 'on'  # SuzyQ plugged
    sbu_flip = self.servod.get('sbu_flip_sel') == 'on'  # SuzyQ flipped
    # Check servo info.
    servo_v4_type = self.servod.get('servo_v4_type')
    servo_v4_fw = self.servod.get('servo_v4_version')
    servo_v4_latest_fw = self.servod.get('servo_v4_latest_version')

    self._logger.error('')
    self._logger.error('CCD diagnosis info:')
    self._logger.error('servo_v4_type is %s' % servo_v4_type)
    self._logger.error('servo_v4 version is %s' % servo_v4_fw)
    self._logger.error('')

    # Check for obsolete firmware.
    if servo_v4_fw != servo_v4_latest_fw:
      self._logger.error("Servo v4 fw version doesn't match latest.")
      self._logger.error("servo-firmware supplies %s" % servo_v4_latest_fw)
      self._logger.error("  Run 'sudo servo_updater -b servo_v4' to correct.")
      self._logger.error('')

    # Check if chargethrough is plugged in.
    if chg_cc1 < NC_LOW and chg_cc2 < NC_LOW:
      self._logger.error('No charger connected to servo')
      self._logger.error('')

    # Check if servo v4 is plugged to a DUT.
    if dut_cc1 < NC_LOW and dut_cc2 < NC_LOW:
      self._logger.error('No DUT plugged into servo')
      self._logger.error('')
    if dut_cc1 > NC_HIGH and dut_cc2 > NC_HIGH:
      self._logger.error('No DUT plugged into servo')
      self._logger.error('')

    # Check if Cr50 USB is present on SBU.
    if sbu1 < NC_LOW and sbu2 < NC_LOW:
      self._logger.error('No USB exported from DUT Cr50')
      self._logger.error('')

    cr50_orientation = None
    if sbu1 > NC_HIGH and sbu2 < NC_LOW:
      cr50_orientation = 'flip'
    if sbu1 < NC_LOW and sbu2 > NC_HIGH:
      cr50_orientation = 'direct'

    suzyq_orientation = 'flip' if sbu_flip else 'direct'

    # Check if Cr50 orientation seems flipped from SuzyQ.
    if cr50_orientation:
      self._logger.error('Cr50 USB detected in '
          '%s orientation' % cr50_orientation)
      self._logger.error('SuzyQ in %s orientation' % suzyq_orientation)
      self._logger.error('')

    # Check if SuzyQ routed to DUT.
    if not sbu_en:
      self._logger.error('SuzyQ disabled in software')
      self._logger.error('')

    # Dump raw voltages and settings.
    self._logger.error('DUT CC: %4dmV %4dmV' % (dut_cc1, dut_cc2))
    self._logger.error('CHG CC: %4dmV %4dmV' % (chg_cc1, chg_cc2))
    self._logger.error('SBU:    %4dmV %4dmV' % (sbu1, sbu2))
    self._logger.error('SuzyQ enabled: '
        '%s, SuzyQ orientation: %s' % (sbu_en, suzyq_orientation))
    self._logger.error('')


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
