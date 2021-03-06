# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=ec.

Provides the following EC controlled function:
  lid_open
  kbd_en
  kbd_m1_a0
  kbd_m1_a1
  kbd_m2_a0
  kbd_m2_a1
  dev_mode (Temporary. See crosbug.com/p/9341)
"""
import logging
import time

import pty_driver

KEY_STATE = [0, 1, 1, 1, 1]

# Key matrix row and column mapped from kbd_m*_a*
KEY_MATRIX = [[[(0, 4), (11, 4)], [(2, 4), None]], [[(0, 2), (11, 2)], [(2, 2),
                                                                        None]]]

# EC console mask for enabling only command channel
COMMAND_CHANNEL_MASK = 0x1


class ecError(pty_driver.ptyError):
  """Exception class for ec."""


class ec(pty_driver.ptyDriver):
  """Object to access drv=ec controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.

  For example, a control to read kbd_en would be dispatched to
  call _Get_kbd_en.
  """

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
        control
      params: dictionary of params needed to perform operations on
        devices. The only params used now is 'subtype', which is used
        by get/set method of base class to decide how to dispatch
        request.
    """
    super(ec, self).__init__(interface, params)
    self._logger.debug('')
    # Add locals to the values dictionary.
    if 'kbd' not in self._interface._uart_state:
        self._interface._uart_state['kbd'] = list(KEY_STATE)

  def _limit_channel(self):
    """Save the current console channel setting and limit the output to the
    command channel (only print output from commands issued on console).

    Raises:
      ecError: when failing to retrieve channel settings
    """
    self._issue_cmd('chan save')
    self._issue_cmd('chan %d' % COMMAND_CHANNEL_MASK)

  def _restore_channel(self):
    """Load saved channel setting"""
    # To improve backward compatibility on EC images that do not have save/
    # restore, set channel mask to power-on default before running restore.
    # TODO(shawnn): Remove this line once all test units have new EC image.
    self._issue_cmd('chan 0xffffffff')

    self._issue_cmd('chan restore')

  def _process_output(self, pre_result):
    """Helper to perform extra formatting out the output of |_Get_output|.

    Formatting is defined in the param 'formatting' and comma separated. It
    is performed in sequence. Supported formatting operations are.
    - strip: strips white-space and new-lines as the end
    - splitlines: split the output by lines and leave as list
    - splitlines_str: split the output by lines and concat as str with
      whitespace

    Args:
      pre_result: str, the output to format

    Returns:
      result, str, after processing from |pre_result|

    """
    if 'formatting' in self._params:
      requests = self._params['formatting'].split(',')
      for request in requests:
        if request == 'strip':
          pre_result = pre_result.strip()
        elif request == 'splitlines':
          pre_result = pre_result.splitlines()
        elif request == 'splitlines_str':
          pre_result = ' '.join(pre_result.splitlines())
        else:
          self._logger.debug('ec output formatting %r unknown. Ignoring.',
                             request)
    return pre_result

  def _Get_output(self):
    """Generic get from EC console, using |self._params| for cmd and regex.

    The required parts to use this abstraction is to provide
    - the console command
    - the regex
    - the group (or 0 if no group) in the regex to report

    The following are _optional_ formatting rules to provide in the formatting
    component, separated by a comma. Unknown requests are logged and ignored.

    Returns:
      result of requested cmd after matching with regex and processing

    Raises:
      ecError: if a required attribute is missing: 'cmd', 'regex', 'group'
      ecError: if the output from the cmd matched with the regex is None
    """
    for req in ['cmd', 'regex', 'group']:
      if req not in self._params:
        raise ecError('%r required for |output|' % req)
    cmd = self._params['cmd']
    regex = self._params['regex']
    group = int(self._params['group'])
    self._limit_channel()
    result = self._issue_cmd_get_results(cmd, [regex])
    self._restore_channel()
    if result is None:
      raise ecError('Failed to retrieve output for %r matching regex %r' %
                    (cmd, regex))
    # Extract the requested group. This control does not support a list of regex
    # but rather just expects one regex. Therefore we access the 1st element of
    # the result (result[0]) always.
    pre_result = result[0][group]
    result = self._process_output(pre_result)
    return result

  def _Get_board(self):
    """Getter of board.

    Returns:
        The board string.
    """
    self._limit_channel()
    result = self._issue_cmd_get_results('ver', ['RO:\s+(\S*)_v?[\d.-]+'])[0]
    self._restore_channel()
    if result is None:
      raise ecError('Cannot retrieve the board result on EC console.')
    return result[1]

  def _Get_active_copy(self):
    """Getter of active_copy.

    Returns:
        The string of the active EC copy, e.g. "RO", "RW", "RW_B".
    """
    self._limit_channel()
    result = self._issue_cmd_get_results('sysinfo', ['Copy:\s+(\S+)\s'])[0]
    self._restore_channel()
    if result is None:
      raise ecError('Cannot retrieve the active copy result on EC console.')
    return result[1]

  def _Get_system_powerstate(self):
    """Getter for the current powerstate
    as reported by powerinfo command.

    Returns:
      The powerinfo string.
    """
    self._limit_channel()
    result = self._issue_cmd_get_results('powerinfo',
                                         ['power state \d+ = (.*), in'])[0]
    self._restore_channel()
    if result is None:
      # TODO(coconutruben): in here, we might be able to detect if we're
      # in G3, by seeking the right exception
      raise ecError('Cannot retrieve the power state on EC console.')
    return result[1]

  def _Get_gpio(self):
    """Getter of current gpio settings.

    Returns:
        ec gpios and their current state 1|0
    """
    self._limit_channel()
    result = self._issue_cmd_get_results('gpioget', ['gpioget.*>'])[0]
    self._restore_channel()
    if result is None:
      raise ecError('Cannot retrieve the ec gpios states on EC console.')
    # [:-1] is to remove the trailing >
    return '\n' + result.replace('gpioget', '').replace('\r', '')[:-1]

  def _set_key_pressed(self, key_rc, pressed):
    """Press/release a key.

    Args:
      key_rc: Tuple containing row and column of the key.
      pressed: 0=release, 1=press.
    """
    if key_rc is None:
      return
    self._issue_cmd('kbpress %d %d %d' % (key_rc + (pressed,)))

  def _get_mx_ax_index(self, m, a):
    """Get the index of a kbd_mx_ax control.

    Args:
      m: Selection of kbd_m1 or kbd_m2. Note the value is 0/1, not 1/2.
      a: Selection of a0 and a1.
    """
    return m * 2 + a + 1

  def _set_both_keys(self, pressed):
    """Press/release both simulated key.

    Args:
      pressed: 0=release, 1=press.
    """
    m1_a0, m1_a1, m2_a0, m2_a1 = self._interface._uart_state['kbd'][1:5]
    self._set_key_pressed(KEY_MATRIX[1][m2_a0][m2_a1], pressed)
    self._set_key_pressed(KEY_MATRIX[0][m1_a0][m1_a1], pressed)

  def _Set_kbd_en(self, value):
    """Enable/disable keypress simulation."""
    self._logger.debug('')
    org_value = self._interface._uart_state['kbd'][0]
    if org_value == 0 and value == 1:
      self._set_both_keys(pressed=1)
    elif org_value == 1 and value == 0:
      self._set_both_keys(pressed=0)
    self._interface._uart_state['kbd'][0] = value

  def _Get_kbd_en(self):
    """Retrieve keypress simulation enabled/disabled.

    Returns:
      0: Keyboard emulation is disabled.
      1: Keyboard emulation is enabled.
    """
    return self._interface._uart_state['kbd'][0]

  def _Set_kbd_mx_ax(self, m, a, value):
    """Implementation of _Set_kbd_m*_a*

    Args:
      m: Selection of kbd_m1 or kbd_m2. Note the value is 0/1, not 1/2.
      a: Selection of a0 and a1.
      value: The new value to set.
    """
    self._logger.debug("")
    org_value = self._interface._uart_state['kbd'][self._get_mx_ax_index(m, a)]
    if self._Get_kbd_en() == 1 and org_value != value:
      org_value = [
        self._interface._uart_state['kbd'][self._get_mx_ax_index(m, 0)],
        self._interface._uart_state['kbd'][self._get_mx_ax_index(m, 1)]
      ]
      new_value = list(org_value)
      new_value[a] = value
      self._set_key_pressed(KEY_MATRIX[m][org_value[0]][org_value[1]], 0)
      self._set_key_pressed(KEY_MATRIX[m][new_value[0]][new_value[1]], 1)
    self._interface._uart_state['kbd'][self._get_mx_ax_index(m, a)] = value

  def _Set_kbd_m1_a0(self, value):
    """Setter of kbd_m1_a0."""
    self._Set_kbd_mx_ax(0, 0, value)

  def _Get_kbd_m1_a0(self):
    """Getter of kbd_m1_a0."""
    return self._interface._uart_state['kbd'][self._get_mx_ax_index(0, 0)]

  def _Set_kbd_m1_a1(self, value):
    """Setter of kbd_m1_a1."""
    self._Set_kbd_mx_ax(0, 1, value)

  def _Get_kbd_m1_a1(self):
    """Getter of kbd_m1_a1."""
    return self._interface._uart_state['kbd'][self._get_mx_ax_index(0, 1)]

  def _Set_kbd_m2_a0(self, value):
    """Setter of kbd_m2_a0."""
    self._Set_kbd_mx_ax(1, 0, value)

  def _Get_kbd_m2_a0(self):
    """Getter of kbd_m2_a0."""
    return self._interface._uart_state['kbd'][self._get_mx_ax_index(1, 0)]

  def _Set_kbd_m2_a1(self, value):
    """Setter of kbd_m2_a1."""
    self._Set_kbd_mx_ax(1, 1, value)

  def _Get_kbd_m2_a1(self):
    """Getter of kbd_m2_a1."""
    return self._interface._uart_state['kbd'][self._get_mx_ax_index(1, 1)]

  def _Get_lid_open(self):
    """Getter of lid_open.

    Returns:
      0: Lid closed.
      1: Lid opened.
    """
    self._limit_channel()
    result = self._issue_cmd_get_results('lidstate',
                                         ['lid state: (open|closed)'])[0]
    self._restore_channel()

    return 1 if result[1] == 'open' else 0

  def _Set_lid_open(self, value):
    """Setter of lid_open.

    Args:
      value: 0=lid closed, 1=lid opened.
    """
    if value == 0:
      self._issue_cmd('lidclose')
    else:
      self._issue_cmd('lidopen')

  def _Get_volume_up(self):
    """Getter of Volup for Ryu"""
    result = self._issue_cmd_get_results('btnpress volup',
                                         ['Button volup pressed = (\d+)'])[0]
    return int(result[1])

  def _Set_volume_up(self, value):
    """Setter of Volup for Ryu

    Args:
      value: 1=button pressed, 0=button released
    """
    self._issue_cmd('btnpress volup %d' % int(value))

  def _Get_volume_down(self):
    """Getter of Voldown for Ryu"""
    result = self._issue_cmd_get_results('btnpress voldown',
                                         ['Button voldown pressed = (\d+)'])[0]
    return int(result[1])

  def _Set_volume_down(self, value):
    """Setter of Voldown for Ryu

    Args:
      value: 1=button pressed, 0=button released
    """
    self._issue_cmd('btnpress voldown %d' % int(value))

  def _Set_button_hold(self, value):
    """Setter for a button hold on the ec.

    'pwrbtn' or button for tablets/detachables.

    Args:
      value: number of ms to hold the volume button. Has to be at least 1.
    """
    if value < 1:
      self._logger.error('Trying to set ec button press to %d ms. Overwriting '
                         'the value to be 1ms.', value)
      value = 1
    # One of 'button' or 'powerbtn'
    cmd = self._params.get('ec_cmd')
    # 'button' cmd requires vup|vdown or both while 'powerbtn' requires
    # no args.
    argline = self._params.get('ec_args', '')
    ec_cmd = '%s %s %d' % (cmd, argline, value)
    self._issue_cmd(ec_cmd)
    # Issuing a console command is async. Wait the button release.
    time.sleep(value/1000.0)

  def _Get_cpu_temp(self):
    """Getter of cpu_temp.

    Reads CPU temperature through PECI. Only works when device is powered on.

    Returns:
      CPU temperature in degree C.
    """
    self._limit_channel()
    result = self._issue_cmd_get_results(
        'temps', ['PECI[ \t]*:[ \t]*[0-9]* K[ \t]*=[ \t]*([0-9]*)[ \t]*C'])[0]
    self._restore_channel()
    if result is None:
      raise ecError('Cannot retrieve CPU temperature.')
    return result[1]

  def _get_battery_values(self):
    """Retrieves various battery related values.

    Battery command in the EC currently exposes the following information:
       Temp:      0x0be1 = 304.1 K (31.0 C)
       Manuf:     SUNWODA
       Device:    S1
       Chem:      LION
       Serial:    0x0000
       V:         0x1ef7 = 7927 mV
       V-desired: 0x20d0 = 8400 mV
       V-design:  0x1ce8 = 7400 mV
       I:         0x06a9 = 1705 mA(CHG)
       I-desired: 0x06a4 = 1700 mA
       Mode:      0x7f01
       Charge:    66 %
         Abs:     65 %
       Remaining: 5489 mAh
       Cap-full:  8358 mAh
         Design:  8500 mAh
       Time-full: 2h:47
         Empty:   0h:0

    This method currently returns a subset of above.

    Returns:
      Dictionary where:
        tempc: battery temperature in degC
        mv: battery voltage in millivolts
        ma: battery amps in milliamps
        mw: battery power in milliwatts
        charge_percent: battery charge in percent
        charge_mah: battery charge in mAh
        full_mah: battery last full charge in mAh
        design_mah: battery design full capacity in mAh
    """
    self._limit_channel()
    results = self._issue_cmd_get_results('battery', [
        r'Temp:[\s0-9a-fx]*= \d+\.\d+ K \((-*\d+\.\d+)',
        r'V:[\s0-9a-fx]*= (-*\d+) mV',
        r'I:[\s0-9a-fx]*= (-*\d+) mA',
        r'Charge:\s*(\d+) %',
        r'Remaining:\s*(\d+) mAh',
        r'Cap-full:\s*(\d+) mAh',
        r'Design:\s*(\d+) mAh',
    ])
    self._restore_channel()
    result = {
        'tempc': float(results[0][1]),
        'mv': int(results[1][1], 0),
        'ma': int(results[2][1], 0) * -1,
        'charge_percent': int(results[3][1], 0),
        'charge_mah': int(results[4][1], 0),
        'full_mah': int(results[5][1], 0),
        'design_mah': int(results[6][1], 0)
    }
    result['mw'] = result['ma'] * result['mv'] / 1000.0
    return result

  def _Get_battery_tempc(self):
    """Retrieves temperature measurements for the battery."""
    return self._get_battery_values()['tempc']

  def _Get_milliamps(self):
    """Retrieves current measurements for the battery."""
    return self._get_battery_values()['ma']

  def _Get_millivolts(self):
    """Retrieves voltage measurements for the battery."""
    return self._get_battery_values()['mv']

  def _Get_milliwatts(self):
    """Retrieves power measurements for the battery."""
    return self._get_battery_values()['mw']

  def _Get_battery_charge_percent(self):
    """Retrieves battery charge in percent for the battery."""
    return self._get_battery_values()['charge_percent']

  def _Get_battery_charge_mah(self):
    """Retrieves battery charge in mAh for the battery."""
    return self._get_battery_values()['charge_mah']

  def _Get_battery_full_charge_mah(self):
    """Retrieves battery last full charge in mAh for the battery."""
    return self._get_battery_values()['full_mah']

  def _Get_battery_full_design_mah(self):
    """Retrieves battery design full capacity in mAh for the battery."""
    return self._get_battery_values()['design_mah']

  def _Get_battery_charging(self):
    """Retrieves whether the battery is charging from chargestate cmd."""
    self._limit_channel()
    cmd = 'chgstate'
    rgx = 'batt_is_charging = (\d)[\r\n]+'
    try:
      results = self._issue_cmd_get_results(cmd, [rgx])
    finally:
      self._restore_channel()
    return bool(int(results[0][1]))

  def _Get_ac_attached(self):
    """Retrieve whether an AC charger is attached."""
    self._limit_channel()
    cmd = 'chgstate'
    rgx = 'ac = (\d)[\r\n]+'
    try:
      results = self._issue_cmd_get_results(cmd, [rgx])
    finally:
      self._restore_channel()
    return bool(int(results[0][1]))

  def _get_pwr_avg(self):
    """Uses ec pwr_avg command to retrieve battery power average.

    pwr_avg function provides a one minute power average based on battery data.

    > pwr_avg
    mv = xxxx
    ma = xxxx
    mw = xxxx

    Returns:
      Dictionary where:
        mv: battery voltage in millivolts
        ma: battery amps in milliamps
        mw: battery power in milliwatts
    """
    self._limit_channel()
    cmd = 'pwr_avg'
    cmd_not_found_regex = "Command '%s' not found" % cmd
    results = self._issue_cmd_get_results(cmd, [
        r'mv = (-?\d+)[\r\n]+'
        'ma = (-?\d+)[\r\n]+'
        'mw = (-?\d+)[\r\n]+|%s' % cmd_not_found_regex
    ])
    self._restore_channel()
    resultline = results[0]
    if cmd_not_found_regex in resultline:
      raise ecError('cmd |%s| is not available on the ec.' % cmd)
    result = {
        'mv': int(results[0][1], 0),
        'ma': int(results[0][2], 0) * -1,
        'mw': int(results[0][3], 0) * -1
    }
    return result

  def _Get_avg_milliamps(self):
    """Retrieves one minute running avg current from the battery."""
    return self._get_pwr_avg()['ma']

  def _Get_avg_millivolts(self):
    """Retrieves one minute running avg voltage from the battery."""
    return self._get_pwr_avg()['mv']

  def _Get_avg_milliwatts(self):
    """Retrieves one minute running avg power from the battery."""
    return self._get_pwr_avg()['mw']

  def _get_fan_values(self):
    """Retrieve fan related values.

    'faninfo' command in the EC exposes the following information:
      Fan actual speed: 6694 rpm
          target speed: 6600 rpm
          duty cycle:   41%
          status:       2
          enabled:      yes
          powered:      yes

    This method returns a subset of above.

    Returns:
      List [fan_act_rpm, fan_trg_rpm, fan_duty] where:
        fan_act_rpm: Actual fan RPM.
        fan_trg_rpm: Target fan RPM.
        fan_duty: Current fan duty cycle.
    """
    self._limit_channel()
    results = self._issue_cmd_get_results('faninfo', [
        'Actual:[ \t]*(\d+) rpm', 'Target:[ \t]*(\d+) rpm', 'Duty:[ \t]*(\d+)%'
    ])
    self._restore_channel()
    return [int(results[0][1], 0), int(results[1][1], 0), int(results[2][1], 0)]

  def _Get_fan_actual_rpm(self):
    """Retrieve actual fan RPM."""
    return self._get_fan_values()[0]

  def _Get_fan_target_rpm(self):
    """Retrieve target fan RPM."""
    return self._get_fan_values()[1]

  def _Get_fan_duty(self):
    """Retrieve current fan duty cycle."""
    return self._get_fan_values()[2]

  def _Set_fan_target_rpm(self, value):
    """Set target fan RPM.

    This function sets target fan RPM or turns on auto fan control.

    Args:
      value: Non-negative values for target fan RPM. -1 is treated as maximum
        fan speed. -2 is treated as auto fan speed control.
    """
    if value == -2:
      self._issue_cmd('autofan')
    else:
      # "-1" is treated as max fan RPM in EC, so we don't need to handle that
      self._issue_cmd('fanset %d' % value)

  def _Get_flash_size(self):
    """Getter of usable EC flash size in Kbytes.

    Returns:
        The flash memory size in Kbytes.
    """
    self._limit_channel()
    result = self._issue_cmd_get_results('flashinfo',
                                         ['(?i)Usable:\s*(\d+)\sKB'])[0]
    self._restore_channel()
    if result is None:
      raise ecError('Cannot retrieve the flash memory size of EC.')
    return result[1]

  def _Get_feat(self):
    """Retrieves the EC feature flags encoded as a hexadecimal."""
    self._limit_channel()
    try:
      result = self._issue_cmd_get_results(
          'feat', ['0-31: (0x[0-9a-f]{8})', '32-63: (0x[0-9a-f]{8})'])
    except pty_driver.ptyError:
      raise ecError('Cannot retrieve the feature flags on EC console.')
    finally:
      self._restore_channel()
    return hex((int(result[1][1], 16) << 32) | int(result[0][1], 16))
