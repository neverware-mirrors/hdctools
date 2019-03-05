# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servo v4 specific controls through ec3po.

Provides the following console controlled function subtypes:
  servo_v4_ccd_mode
"""

import logging
import time

import ec3po_servo
import pty_driver
import servo


class ec3poServoV4Error(Exception):
  """Exception class."""


class ec3poServoV4(ec3po_servo.ec3poServo):
  """Object to access drv=ec3po_servo_v4 controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.
  """
  SWAP_DELAY = 1
  DUT_PORT = 1

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: ec3po interface object to handle low-level communication to
        control
      params: dictionary of params needed
    Raises:
      ec3poServoV4Error: on init failure
    """
    super(ec3poServoV4, self).__init__(interface, params)

    self._logger.debug('')

  def _Get_version(self):
    """Getter of version.

    Returns:
        The version string
    """
    result = self._issue_safe_cmd_get_results('ver', ['Build:\s+(\S+)\s'])[0]
    if result is None:
      raise ec3poServoV4Error('Cannot retrieve the version.')
    return result[1]

  def _Set_version(self, value):
    """'Setter' of version.

    Args:
        value: should equal print/0
    Prints:
        The version string
    """
    version = self._Get_version()
    self._logger.info('------------- servo v4 version: %s', version)

  def batch_set(self, batch, index):
    """Set a batch of values on console gpio.

    Args:
      batch: dict of GPIO names, and on/off value
      index: index of batch preset
    """
    if index not in range(len(batch.values()[0])):
      raise ec3poServoV4Error('Index %s out of range' % index)

    cmds = []
    for name, values in batch.items():
      cmds.append('gpioset %s %s\r' % (name, values[index]))

    self._issue_cmd(cmds)

  def servo_adc(self):
    """Get adc state info from servo V4.

    returns:
      (chg_cc1, chg_cc2, dut_cc1, dut_cc2, sbu1, sbu2) tuple of float in mv.

    > adc
    CHG_CC1_PD = 1648
    CHG_CC2_PD = 34
    DUT_CC1_PD = 1694
    DUT_CC2_PD = 991
    SBU1_DET = 2731
    SBU2_DET = 92
    SUB_C_REF = 565
    """
    rx = ['(CHG_CC1_PD) = (\d+)',
          '(CHG_CC2_PD) = (\d+)',
          '(DUT_CC1_PD) = (\d+)',
          '(DUT_CC2_PD) = (\d+)',
          '(SBU1_DET) = (\d+)',
          '(SBU2_DET) = (\d+)']

    res = self._issue_safe_cmd_get_results('adc', rx)

    if len(res) != 6:
      raise ec3poServoV4Error("Can't receive cc info: [%s]" % results)

    vals = {entry[1] : entry[2] for entry in res}

    return vals

  def _Get_adc(self):
    """Get adc value.

    Args:
      name: adc name.
    """
    if 'adc_name' in self._params:
      name = self._params['adc_name']
    else:
      raise ec3poServoV4Error("'adc_name' not in _params")

    vals = self.servo_adc()

    if name not in vals:
      raise ec3poServoV4Error(
          "adc_name '%s' not in adc set %s" % (name, vals.keys()))

    return vals[name]

  def servo_cc_modes(self):
    """Get cc line state info from servo V4.

    returns:
      (dts, charging, charge_enabled) tuple of on/off.

    > cc
    dts mode: on
    chg mode: off
    chg allowed: off
    """
    rx = ['dts mode:\s*(off|on)', 'chg mode:\s*(off|on)',
          'chg allowed:\s*(off|on)']

    res = self._issue_safe_cmd_get_results('cc', rx)

    if len(res) != 3:
      raise ec3poServoV4Error("Can't receive cc info: [%s]" % results)

    dts = res[0][1]
    chg = res[1][1]
    mode = res[2][1]

    return (dts, chg, mode)

  def lookup_cc_setting(self, mode, dts):
    """Composite settings into cc commandline arg.

    Args:
      mode: 'on'/'off' setting for charge enable
      dts:  'on'/'off' setting for dts enable

    Returns:
      string: 'src', 'snk', 'srcdts', 'snkdts' as appropriate.
    """
    newdts = 'dts' if (dts == 'on') else ''
    newmode = 'src' if (mode == 'on') else 'snk'

    newcc = newmode + newdts

    return newcc

  def _Get_servo_v4_dts_mode(self):
    """Getter of servo_v4_dts_mode.

    Returns:
      "off": DTS mode is disabled.
      "on": DTS mode is enabled.
    """
    dts, chg, mode = self.servo_cc_modes()

    return dts

  def _Set_servo_v4_dts_mode(self, value):
    """Setter of servo_v4_dts_mode.

    Args:
      value: "off", "on"
    """
    if value == 'off' or value == 'on':
      dts, chg, mode = self.servo_cc_modes()
      newcc = self.lookup_cc_setting(mode, value)

      self._issue_cmd('cc %s' % newcc)
    else:
      raise ValueError("Invalid dts_mode setting: '%s'. Try one of "
                       "'on' or 'off'." % value)

  def _get_pd_info(self, port):
    """Get the current PD state

    Args:
      port: Type C PD port 0/1
    Returns:
      "src|snk" for role and state value
    """
    pd_cmd = 'pd %s state' % port
    # Two FW versions for this command, get full line.
    m = self._issue_safe_cmd_get_results(pd_cmd,
        ['State:\s+([\w]+)_([\w]+)'])[0]
    if m is None:
      raise ec3poServoV4Error('Cannot retrieve pd state.')

    info = {}
    info['role'] = m[1].lower()
    info['state'] = m[2].lower()

    return info

  def _Get_servo_v4_power_role(self):
    """Setter of servo_v4_role.

    @returns: Current power role
    """
    dts, chg, mode = self.servo_cc_modes()

    return 'src' if (chg == 'on') else 'snk'

  def _Set_servo_v4_power_role(self, role):
    """Setter of servo_v4_power_role.

    Args:
      role: "src", "snk"
    """
    if role == 'src' or role == 'snk':
      dts, chg, mode = self.servo_cc_modes()
      newrole = 'on' if role == 'src' else 'off'
      newcc = self.lookup_cc_setting(newrole, dts)

      self._issue_cmd('cc %s' % newcc)
    else:
      raise ValueError("Invalid power role setting: '%s'. Try one of "
                       "'src' or 'snk'." % value)

  def _Get_servo_v4_ccd_keepalive(self):
    """Get keepalive status.

    Returns:
       1 if keepalive is enabled, 0 if it's not.
    """
    _, status = self._issue_safe_cmd_get_results('keepalive',
         ['ccd_keepalive: ([a-zA-Z]+)'])[0]
    if status == 'enabled':
      return 1

    return 0

  def _Set_servo_v4_ccd_keepalive(self, enable):
    """Set servo_v4_ccd_keepalive.

    Note: When keepalive is enabled, it will remain enabled until explicitly
    disabled.

    Args:
      enable: An integer indicating if keepalive should be enabled (non-zero),
              otherwise disabled.
    """
    if enable:
      val = 'enable'
    else:
      val = 'disable'

    self._issue_cmd('keepalive %s' % val)
