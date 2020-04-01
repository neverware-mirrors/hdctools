# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servo v4 specific controls through ec3po.

Provides the following console controlled function subtypes:
  servo_v4_ccd_mode
"""
import re

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

  # The base regex to match a mac address.
  RE_BASE_MACADDR = r'([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})'

  # This regex is used to validate input to the setter.
  RE_MACADDR_INPUT = re.compile(r'%s$' % RE_BASE_MACADDR)

  # This regex is used to extract the macaddr from the conosle.
  RE_MACADDR_EXTRACT = r'MAC address: (%s|Unitialized)[\n\r ]' % RE_BASE_MACADDR

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
      A dict of status, with keys ('dts', 'charging', 'charge_enabled',
      'polarity', 'pd_comm')

    > cc
    cc: on
    dts mode: on
    chg mode: off
    chg allowed: off
    drp enabled: off
    cc polarity: cc1
    pd enabled: on
    """
    rx = ['dts mode:\s*(off|on)', 'chg mode:\s*(off|on)',
          'chg allowed:\s*(off|on)']
    res = self._issue_safe_cmd_get_results('cc', rx)

    if len(res) != len(rx):
      raise ec3poServoV4Error("Can't receive cc info: [%s]" % res)

    cc_dict = {'dts': res[0][1], 'chg': res[1][1], 'mode': res[2][1]}

    # TODO(waihong): Move the optional match to mandatory when the old
    # firmware is phased out.
    def _get_optional_field(rx, default, warn_str):
      """Get the optional fields of comand cc.

        Returns 'default' if failed to parse the value.

        Args:
          rx: a string for regex pattern
          default: a default value when parse fail
          warn_str: a string to warn when fail to obatin the field

        Returns:
          The regexed string if success, and "default" otherwise
      """
      try:
        optional_res = self._issue_safe_cmd_get_results('cc', [rx])
        return optional_res[0][1]
      except pty_driver.ptyError:
        self._logger.warn('%s unsupported, return %s. Update the servo v4 fw.' %
                          (warn_str, str(default)))
      return default

    # Old firmware can't change CC polarity, i.e. always cc1.
    cc_dict['pol'] = _get_optional_field('cc polarity:\s*(cc1|cc2)', 'cc1',
                                         'CC polarity')

    # Old firmware can't control PD comm, it always the same as 'chg allowed'.
    cc_dict['pd'] = _get_optional_field('pd enabled:\s*(off|on)',
                                        cc_dict['chg'], 'PD comm')

    return cc_dict

  def lookup_cc_setting(self, mode, dts, snk_with_pd):
    """Composite settings into cc commandline arg.

    Args:
      mode: 'on'/'off' setting for charge enable
      dts:  'on'/'off' setting for dts enable
      snk_with_pd: 'on / off' setting for sink with PD.

    Returns:
      string: 'src', 'snk', 'pdsnk', 'srcdts', 'snkdts', 'pdsnkdts' as
              appropriate.
    """
    newdts = 'dts' if (dts == 'on') else ''
    newmode = 'src' if (mode == 'on') else 'snk'
    newpd = 'pd' if (newmode == 'snk' and snk_with_pd == 'on') else ''

    newcc = newpd + newmode + newdts

    return newcc

  def max_req_voltage(self):
    """Get max request voltage from servo V4.

    Returns:
      string of voltage, like '20v'
    """
    rx = [r'max req:\s*(\d+)000mV']
    res = self._issue_safe_cmd_get_results('pd 1 dev', rx)

    if len(res) != len(rx):
      raise ec3poServoV4Error("Can't receive voltage info: [%s]" % res)

    return res[0][1] + 'v'

  def adapter_source_capability(self):
    """Get a list of PDO strings.

    Returns:
      a list of PDO strings: e.g. ["0: 5000mV/3000mA", "1: 9000mV/3000mA"]
    """
    rx = [r'\d: \d*mV/\d*mA']
    res = self._issue_safe_cmd_get_multi_results('ada_srccaps', rx)

    if not len(res):
      raise ec3poServoV4Error('No Adapter SrcCap. Maybe charger not plugged or '
                              'servo v4 firmware too old?')
    return res

  def _Get_ada_srccaps(self):
    """Getter of ada_srccaps

    Returns:
      a list of PDO strings: e.g. ["0: 5000mV/3000mA", "1: 9000mV/3000mA"]
    """
    return self.adapter_source_capability()

  def _Get_servo_v4_dts_mode(self):
    """Getter of servo_v4_dts_mode.

    Returns:
      "off": DTS mode is disabled.
      "on": DTS mode is enabled.
    """
    return self.servo_cc_modes()['dts']

  def _Set_servo_v4_dts_mode(self, value):
    """Setter of servo_v4_dts_mode.

    Args:
      value: "off", "on"
    """
    if value == 'off' or value == 'on':
      cc_dict = self.servo_cc_modes()
      newcc = self.lookup_cc_setting(cc_dict['mode'], value, cc_dict['pd'])

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

  def _Get_servo_v4_pd_comm(self):
    """Getter of servo_v4 DUT port PD communication capbility.

    Returns: a string for 'on' or 'off'
    """
    return self.servo_cc_modes()['pd']

  def _Set_servo_v4_pd_comm(self, value):
    """Setter of servo_v4 DUT port PD communication capbility.

    Args:
      value: 'on' or 'off'
    """
    cc_dict = self.servo_cc_modes()
    role = 'src' if cc_dict['chg'] == 'on' else 'snk'

    if role == 'snk' and (value == 'on' or value == 'off'):
      newcc = self.lookup_cc_setting(cc_dict['mode'], cc_dict['dts'], value)
      self._issue_cmd('cc %s' % newcc)
    elif role == 'src' and value == 'on':
      # Intentionally passthrough, PD comm is enabled at SRC role.
      pass
    else:
      raise ValueError('Invalid PD comm setting: %s. PD comm can only '
                       'be config at SNK role' % value)

  def _Get_servo_v4_power_role(self):
    """Getter of servo_v4_role.

    Returns:
      Current power role, like "src", "snk"
    """
    chg = self.servo_cc_modes()['chg']

    return 'src' if (chg == 'on') else 'snk'

  def _Set_servo_v4_power_role(self, role):
    """Setter of servo_v4_power_role.

    Args:
      role: "src", "snk"
    """
    if role == 'src' or role == 'snk':
      dts = self.servo_cc_modes()['dts']
      newrole = 'on' if role == 'src' else 'off'
      # SNK role defaults to disable PD comm, and SRC role defaults to enable
      newpd = 'on' if role == 'src' else 'off'
      newcc = self.lookup_cc_setting(newrole, dts, newpd)

      self._issue_cmd('cc %s' % newcc)
    else:
      raise ValueError("Invalid power role setting: '%s'. Try one of "
                       "'src' or 'snk'." % value)

  def _Set_usbc_role(self, value):
    """Setter of usbc_role.

    TODO(b:140256624): Should be deprecated by _Set_usbc_pr

    Args:
      value: 0 for dev, 1 for 5v, 2 for 12v, 3 for 20v
    """
    self._issue_cmd('usbc_action %s' % self.USBC_ACTION_ROLE[value])

  def _Get_usbc_role(self):
    """Getter of usbc_role.

    TODO(b:140256624): Should be deprecated by _Get_usbc_pr

    Returns:
      0 for dev, 1 for 5v, 2 for 12v, 3 for 20v
    """
    mode = self.servo_cc_modes()['mode']

    # Sink mode, return 0 for dev.
    if mode == 'off':
      return 0

    vol = self.max_req_voltage()
    if vol in self.USBC_ACTION_ROLE:
      return self.USBC_ACTION_ROLE.index(vol)

    raise ValueError("Invalid voltage: '%s'" % vol)

  def _Set_usbc_pr(self, value):
    """Setter of usbc_pr.

    Args:
      value: 0 for dev, 5 for 5v, 12 for 12v, 20 for 20v, etc.
    """
    if value == 0:
      self._issue_cmd('usbc_action dev')
      return

    try:
      self._issue_cmd_get_results(
          'usbc_action chg %s' % str(value), [r'CHG SRC \d+mV'], timeout=1)
    except pty_driver.ptyError:
      # TODO(b:140256624): This is a hack to ensure chg subcmd exists.
      # Drop this when we phase out the old servo_v4 firmware.
      raise ec3poServoV4Error('Unsupported command, update servo_v4 firmware')

  def _Get_usbc_pr(self):
    """Getter of usbc_pr.

    Returns:
      0 for dev, 5 for 5v, 9 for 9v, 20 for 20v, etc.
    """
    mode = self.servo_cc_modes()['mode']

    # Sink mode, return 0 for dev.
    if mode == 'off':
      return 0

    # drop 'v'. e.g. '20v' -> 20
    return int(self.max_req_voltage()[:-1])

  def _Set_usbc_polarity(self, value):
    """Setter of usbc_polarity.

    Args:
      value: 0 for CC1, 1 for CC2
    """

    cc_dict = self.servo_cc_modes()
    cc = self.lookup_cc_setting(cc_dict['mode'], cc_dict['dts'], cc_dict['pd'])
    self._issue_cmd('cc %s %s' % (cc, self.CC_POLARITY[value]))

  def _Get_usbc_polarity(self):
    """Getter of usbc_polarity.

    Returns:
      0 for CC1, 1 for CC2
    """
    pol = self.servo_cc_modes()['pol']
    return self.CC_POLARITY.index(pol)

  def _Set_macaddr(self, macaddr):
    """Setter of macaddr.

    Args:
      macaddr: mac address to set.
    Raises:
      ec3poServoV4Error: if |macaddr| doesn't match with |RE_MACADDR_INPUT|
      ec3poServoV4Error: if |macaddr| is not the stored value in the end
    """
    macaddr = macaddr.lower()
    if not re.match(self.RE_MACADDR_INPUT, macaddr):
      raise ec3poServoV4Error('%r does not match mac address regex %r' %
                              (macaddr, self.RE_BASE_MACADDR))
    self._issue_cmd('macaddr set %s' % macaddr)
    # Lastly, validate that the set worked as intended.
    stored_macaddr = self._Get_macaddr()
    if stored_macaddr != macaddr:
      raise ec3poServoV4Error('Tried setting macaddr cache to %r but got %r.' %
                              (macaddr, stored_macaddr))

  def _Get_macaddr(self):
    """Getter of macaddr.

    Returns:
      cached mac address.
    """
    res = self._issue_safe_cmd_get_results('macaddr',
                                           [self.RE_MACADDR_EXTRACT])
    # The first group is the actual mac address.
    return res[0][1]
