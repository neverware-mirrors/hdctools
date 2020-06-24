# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import cros_ec_power
import ec


class crosEcSoftrecPower(cros_ec_power.CrosECPower):
  """Driver for power_state that uses the EC to trigger recovery.

  A number of boards (generally, the ARM based boards and some x86
  based board) require using the EC to trigger recovery mode.
  """
  # Recovery types.
  _REC_TYPE_REC_ON = 'rec_on'
  _REC_TYPE_REC_OFF = 'rec_off'
  _REC_TYPE_REC_OFF_CLEARB = 'rec_off_clearb'
  _REC_TYPE_FASTBOOT = 'fastboot'
  _REC_TYPE_REC_ON_FORCE_MRC = 'rec_on_force_mrc'

  # Corresponding hostevent commands entered on the EC.
  _HOSTEVENT_CMD_REC_ON = 'hostevent set 0x4000'
  _HOSTEVENT_CMD_REC_OFF = 'hostevent clear 0x4000'
  _HOSTEVENT_CMD_REC_OFF_CLEARB = 'hostevent clearb 0x4000'
  _HOSTEVENT_CMD_FASTBOOT = 'hostevent set 0x1000000'
  _HOSTEVENT_CMD_REC_ON_FORCE_MRC = 'hostevent set 0x20004000'

  _REC_TYPE_HOSTEVENT_CMD_DICT = {
      _REC_TYPE_REC_ON: _HOSTEVENT_CMD_REC_ON,
      _REC_TYPE_REC_OFF: _HOSTEVENT_CMD_REC_OFF,
      _REC_TYPE_REC_OFF_CLEARB: _HOSTEVENT_CMD_REC_OFF_CLEARB,
      _REC_TYPE_FASTBOOT: _HOSTEVENT_CMD_FASTBOOT,
      _REC_TYPE_REC_ON_FORCE_MRC: _HOSTEVENT_CMD_REC_ON_FORCE_MRC
  }

  # Time in seconds to allow the EC to pick up the recovery
  # host event.
  _RECOVERY_DETECTION_DELAY = 1

  # Interface name for USB3 power enabled.
  _USB3_PWR_EN = 'usb3_pwr_en'

  # EC feature bit for EFS2.
  _EC_FEATURE_EFS2 = 1 << 38

  def __init__(self, interface, params):
    """Constructor

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(crosEcSoftrecPower, self).__init__(interface, params)
    # Delay to allow boot into recovery before passing back control.
    self._boot_to_rec_screen_delay = float(
        self._params.get('boot_to_rec_screen_delay', 5.0))
    # Short delay to allow settle between hostevents.
    self._hostevent_delay = float(
        self._params.get('hostevent_delay', 0.1))
    self._warm_reset_can_hold_ap = ('yes' == self._params.get(
        'warm_reset_can_hold_ap', 'yes'))
    self._wait_ext_is_fake = ('yes' == self._params.get(
        'wait_ext_is_fake', 'no'))
    self._role_swap_delay = float(
        self._params.get('role_swap_delay', 1.0))
    self._pb_init_idle = ('yes' == self._params.get('pb_init_idle', 'no'))
    # Time in seconds to wait after booting the AP to reboot the EC.
    self._reset_delay = float(
        self._params.get('reset_delay', 1.0))
    self._power_key = self._params.get('power_key', 'short_press')
    self._usb_power_restore = (
        ('yes' == self._params.get('usb_power_restore', 'no'))
        and interface._syscfg.is_control(self._USB3_PWR_EN))
    self._on = 'on'
    self._off = 'off'

  def _usb3_pwr_disable(self):
    """Disables the USB 3 power (if available and turned on) by turning it off.

    Returns:
      True if disabled (i.e., need to restore later), otherwise False.
    """
    if not self._usb_power_restore:
      return False

    # Some FAFT tests (e.g, platform_ServoPowerStateController*) will set
    # usb3_pwr_en to off to test booting system into recovery mode (without
    # booting from USB) so we want to reset only when usb3_pwr_en is turned on.
    state = self._interface.get(self._USB3_PWR_EN)
    self._logger.debug('%s state: %s', self._USB3_PWR_EN, state);
    if state != self._on:
      return False

    self._logger.debug('Reset %s to %s', self._USB3_PWR_EN, self._off)
    self._interface.set(self._USB3_PWR_EN, self._off)
    return True

  def _usb3_pwr_restore(self):
    """Returns (turns on) USB3 power."""
    self._logger.debug('Set %s to %s', self._USB3_PWR_EN, self._on)
    self._interface.set(self._USB3_PWR_EN, self._on)

  def _power_on_ap(self):
    """Power on the AP after initializing recovery state."""
    need_to_restore = self._usb3_pwr_disable()

    self._interface.set('power_key', self._power_key)

    if need_to_restore:
      self._usb3_pwr_restore()

  def _power_on_bytype(self, rec_mode, rec_type=_REC_TYPE_REC_ON):
    self._interface.set('ec_uart_regexp', 'None')
    self._interface.set('ec_uart_cmd', '\r')
    if rec_mode == self.REC_ON or rec_mode == self.REC_ON_FORCE_MRC:
      if self._warm_reset_can_hold_ap:
        # Hold warm reset so the AP doesn't boot when EC reboots.
        # Note that this only seems to work reliably for ARM devices.
        self._interface.set('warm_reset', 'on')

      try:
        efs2 = bool(int(self._interface.get('ec_feat'), 16) &
                    crosEcSoftrecPower._EC_FEATURE_EFS2)
      except ec.ecError:
        # Assume EFS2 is unsupported if the EC doesn't support the feat
        # command.
        efs2 = False
      ap_off_option = 'ap-off-in-ro' if efs2 else 'ap-off'
      try:
        if self._wait_ext_is_fake:
          raise Exception("wait-ext isn't supported")
        # Before proceeding, we should really check that the EC has reset from
        # our command.  Pexpect is minimally greedy so we won't be able to match
        # the exact reset cause string.  But, this should be good enough.
        self._interface.set('ec_uart_regexp', '["Waiting"]')
        self._interface.set('ec_uart_cmd', 'reboot wait-ext %s' %
                            ap_off_option)
        # Reset the EC to force it back into RO code; this clears
        # the EC_IN_RW signal, so the system CPU will trust the
        # upcoming recovery mode request.
        self._cold_reset()
      except:
        # If the EC doesn't support wait-ext, fallback to the old route.
        # Reset the EC to force it back into RO code; this clears
        # the EC_IN_RW signal, so the system CPU will trust the
        # upcoming recovery mode request.
        # For devices whose warm_reset can't hold AP, AP may boot faster that
        # the original recovery reason is overwritten.
        self._cold_reset()
        # The following "reboot ap-off" command should be sent instantly.
        # During boot-up, EC dumps massive messages. Flushing the incoming
        # messages will delay the command. Should disable flushing.
        self._interface.set('ec_uart_flush', 'off')
        # Send reboot command to EC with only the ap-off argument.
        # This will still prevent a race condition between the
        # EC and AP when rebooting. However, the reboot will be triggered
        # internally by the EC watchdog, and there is no external reset signal.
        self._interface.set('ec_uart_regexp', '["Rebooting!"]')
        self._interface.set('ec_uart_cmd', 'reboot %s' % ap_off_option)
      finally:
        self._interface.set('ec_uart_regexp', 'None')
        self._interface.set('ec_uart_flush', 'on')

      self._logger.debug('Reset recovery wait: %s', self._reset_recovery_time)
      time.sleep(self._reset_recovery_time)

      if self._warm_reset_can_hold_ap:
        # Release warm reset after a potential cold reset settles.
        self._interface.set('warm_reset', 'off')

    else:
      # Need to clear the flag in secondary (B) copy of the host events if
      # we're in non-recovery mode.
      cmd = self._REC_TYPE_HOSTEVENT_CMD_DICT[self._REC_TYPE_REC_OFF_CLEARB]
      try:
        self._interface.set('ec_uart_regexp', '["Events:"]')
        self._interface.set('ec_uart_cmd', cmd)
      finally:
        self._interface.set('ec_uart_regexp', 'None')

    # Tell the EC to tell the CPU we're in recovery mode or non-recovery mode.
    self._logger.debug('Hostevent delay: %s', self._hostevent_delay)
    time.sleep(self._hostevent_delay)
    cmd = self._REC_TYPE_HOSTEVENT_CMD_DICT[rec_type]
    try:
      self._interface.set('ec_uart_regexp', '["Events:"]')
      self._interface.set('ec_uart_cmd', cmd)
    finally:
      self._interface.set('ec_uart_regexp', 'None')
    self._logger.debug('Recovery detection delay: %s',
        self._RECOVERY_DETECTION_DELAY)
    time.sleep(self._RECOVERY_DETECTION_DELAY)

    self._power_on_ap()
    if rec_mode == self.REC_ON or rec_mode == self.REC_ON_FORCE_MRC:
      # Allow time to reach the recovery screen before yielding control.
      self._logger.debug('Boot to rec screen delay: %s',
          self._boot_to_rec_screen_delay)
      time.sleep(self._boot_to_rec_screen_delay)

      # If we are using CCD, make sure the DUT's Type-C port is a DFP so that
      # the ethernet and USB ports will be connected.  Since servo_v4 has the
      # power role of source, its data role is a "downstream facing port" (DFP)
      # and therefore making the DUT's role an "upstream facing port" (UFP).
      # When the data roles are as such, the ethernet port and USB/microSD ports
      # will not be connected to the DUT.  Therefore, we will need to trigger a
      # data role swap by via the EC console.
      #
      # This is needed because the data role swaps normally don't happen in
      # EC_RO (which is the image we MUST be in for entering recovery mode).
      servo_type = self._interface.get('servo_type')
      if 'ccd' in servo_type and 'servo_micro' not in servo_type:
        try:
          # Check current data role.  Assuming port 0 is the CCD port.
          cmd = 'pd 0 state'
          self._interface.set('ec_uart_regexp', '["SNK-UFP"]')
          self._interface.set('ec_uart_cmd', 'pd 0 state')
          self._logger.debug('Initiating data role swap...')
          # Clear the regexp.
          self._interface.set('ec_uart_regexp', 'None')
          cmd = 'pd 0 swap data'
          self._interface.set('ec_uart_cmd', cmd)

          # Did it work?
          try:
            self._logger.debug('Role swap delay: %s',
                self._role_swap_delay)
            time.sleep(self._role_swap_delay)
            cmd = 'pd 0 state'
            self._interface.set('ec_uart_regexp', '["DFP"]')
            self._interface.set('ec_uart_cmd', 'pd 0 state')
            self._logger.debug('Checking data role swap...')
            self._interface.set('ec_uart_regexp', 'None')
          except Exception as e:
            self._logger.error('DUT cannot enable DFP!')
        except Exception as e:
          # Assuming the DUT's data role is already a DFP.
          self._logger.debug('DUT\'s port may already be a DFP.')
          pass
        finally:
          # Clear the regexp.
          self._interface.set('ec_uart_regexp', 'None')

  def _power_on(self, rec_mode):
    if rec_mode == self.REC_ON:
      rec_type = self._REC_TYPE_REC_ON
    elif rec_mode == self.REC_ON_FORCE_MRC:
      rec_type = self._REC_TYPE_REC_ON_FORCE_MRC
    else:
      rec_type = self._REC_TYPE_REC_OFF

    self._power_on_bytype(rec_mode, rec_type)

  def _power_on_fastboot(self):
    self._power_on_bytype(self.REC_ON, rec_type=self._REC_TYPE_FASTBOOT)

  def _reset_cycle(self):
    if self._pb_init_idle:
      try:
        self._interface.set('ec_uart_regexp', '["power state 3 = S0"]')
        self._interface.set('ec_uart_cmd', 'powerinfo')
        dut_was_off = False
      except Exception:
        dut_was_off = True
      finally:
        self._interface.set('ec_uart_regexp', 'None')

      if dut_was_off:
        # Boot the AP so the EC will boot the AP again after it reboots.
        self._power_on(self.REC_OFF)
        time.sleep(self._reset_delay)

    return super(crosEcSoftrecPower, self)._reset_cycle()
