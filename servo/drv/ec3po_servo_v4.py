# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servo v4 specific controls through ec3po.

Provides the following console controlled function subtypes:
  servo_v4_ccd_mode
"""

import time

import ec3po_servo
import pty_driver
import servo


class ec3poServoV4Error(pty_driver.ptyError):
  """Exception class."""


class ec3poServoV4(ec3po_servo.ec3poServo):
  """Object to access drv=ec3po_servo_v4 controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.
  """
  SWAP_DELAY = 1
  DUT_PORT = 1

  USBC_ACTION_ROLE = ['dev', '5v', '12v', '20v']

  CC_POLARITY = ['cc1', 'cc2']

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: ec3po interface object to handle low-level communication to
        control
      params: dictionary of params needed
    Raises:
      ec3poServoV4Error: on init failure
    """
    ec3po_servo.ec3poServo.__init__(self, interface, params, board='servo_v4')

    self._logger.debug('')

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

    if len(res) != len(rx):
      raise ec3poServoV4Error("Can't receive adc info: [%s]" % res)

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
      (dts, charging, charge_enabled, polarity) tuple of on/off.

    > cc
    cc: on
    dts mode: on
    chg mode: off
    chg allowed: off
    drp enabled: off
    cc polarity: cc1
    """
    rx = ['dts mode:\s*(off|on)', 'chg mode:\s*(off|on)',
          'chg allowed:\s*(off|on)']
    res = self._issue_safe_cmd_get_results('cc', rx)

    if len(res) != len(rx):
      raise ec3poServoV4Error("Can't receive cc info: [%s]" % res)

    dts = res[0][1]
    chg = res[1][1]
    mode = res[2][1]
    # Old firmware can't change CC polarity, i.e. always cc1.
    pol = 'cc1'

    # TODO(waihong): Move the optional match to mandatory when the old
    # firmware is phased out.
    try:
      optional_rx = ['cc polarity:\s*(cc1|cc2)']
      optional_res = self._issue_safe_cmd_get_results('cc', optional_rx)
      pol = optional_res[0][1]
    except pty_driver.ptyError:
      self._logger.warn("CC polarity not supported. Update the servo v4 fw.")
      pass

    return (dts, chg, mode, pol)

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

  def max_req_voltage(self):
    """Get max request voltage from servo V4.

    Returns:
      string of voltage, like '20v'
    """
    rx = ['max req:\s*(\d+)000mV']
    res = self._issue_safe_cmd_get_results('pd 1 dev', rx);

    if len(res) != len(rx):
      raise ec3poServoV4Error("Can't receive voltage info: [%s]" % res)

    return res[0][1] + 'v'

  def _Get_servo_v4_dts_mode(self):
    """Getter of servo_v4_dts_mode.

    Returns:
      "off": DTS mode is disabled.
      "on": DTS mode is enabled.
    """
    dts, _, _, _ = self.servo_cc_modes()

    return dts

  def _Set_servo_v4_dts_mode(self, value):
    """Setter of servo_v4_dts_mode.

    Args:
      value: "off", "on"
    """
    if value == 'off' or value == 'on':
      _, _, mode, _ = self.servo_cc_modes()
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
    """Getter of servo_v4_role.

    Returns:
      Current power role, like "src", "snk"
    """
    _, chg, _, _ = self.servo_cc_modes()

    return 'src' if (chg == 'on') else 'snk'

  def _Set_servo_v4_power_role(self, role):
    """Setter of servo_v4_power_role.

    Args:
      role: "src", "snk"
    """
    if role == 'src' or role == 'snk':
      dts, _, _, _ = self.servo_cc_modes()
      newrole = 'on' if role == 'src' else 'off'
      newcc = self.lookup_cc_setting(newrole, dts)

      self._issue_cmd('cc %s' % newcc)
    else:
      raise ValueError("Invalid power role setting: '%s'. Try one of "
                       "'src' or 'snk'." % value)

  def _Set_usbc_role(self, value):
    """Setter of usbc_role.

    Args:
      value: 0 for dev, 1 for 5v, 2 for 12v, 3 for 20v
    """
    self._issue_cmd('usbc_action %s' % self.USBC_ACTION_ROLE[value])

  def _Get_usbc_role(self):
    """Getter of usbc_role.

    Returns:
      0 for dev, 1 for 5v, 2 for 12v, 3 for 20v
    """
    _, _, mode, _ = self.servo_cc_modes()

    # Sink mode, return 0 for dev.
    if mode == 'off':
      return 0

    vol = self.max_req_voltage()
    if vol in self.USBC_ACTION_ROLE:
      return self.USBC_ACTION_ROLE.index(vol)

    raise ValueError("Invalid voltage: '%s'" % vol)

  def _Set_usbc_polarity(self, value):
    """Setter of usbc_polarity.

    Args:
      value: 0 for CC1, 1 for CC2
    """
    dts, _, mode, _ = self.servo_cc_modes()
    cc = self.lookup_cc_setting(mode, dts)
    self._issue_cmd('cc %s %s' % (cc, self.CC_POLARITY[value]))

  def _Get_usbc_polarity(self):
    """Getter of usbc_polarity.

    Returns:
      0 for CC1, 1 for CC2
    """
    _, _, _, pol = self.servo_cc_modes()
    return self.CC_POLARITY.index(pol)
