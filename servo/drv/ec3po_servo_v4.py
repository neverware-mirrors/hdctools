# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servo v4 specific controls through ec3po.

Provides the following console controlled function subtypes:
  servo_v4_ccd_mode
"""

import logging
import time

import pty_driver
import servo

# EC console mask for enabling only command channel
COMMAND_CHANNEL_MASK = 0x1

# servo v4 firmware versions verified compatible with servod
VALID_VERSIONS = ['servo_v4_v1.1.5734-4a47178']


class ec3poServoV4Error(Exception):
  """Exception class."""


class ec3poServoV4(pty_driver.ptyDriver):
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

    if 'console' in params:
      if params['console'] == 'enhanced' and \
          type(interface) is servo.ec3po_interface.EC3PO:
        interface._console.oobm_queue.put('interrogate never enhanced')
      else:
        raise ec3poServoV4Error('Enhanced console must be ec3po!')

    self._logger.debug('')

  def _Get_ver(self):
    """Getter of ver.

    Returns:
        The version string
    """
    result = self._issue_cmd_get_results('ver', ['Build:\s+(\S+)\s'])[0]
    if result is None:
      raise ec3poServoV4Error('Cannot retrieve the version.')
    return result[1]

  def _Get_ver_valid(self):
    """Getter of ver_valid.

    Returns:
        Boolean: Is the version string one of the validated versions?
    """
    ver = self._Get_ver()
    valid = ver in VALID_VERSIONS
    if not valid:
      logging.warn('Detected servo v4 version: %s', ver)
      logging.warn('Not in valid versions: %s', VALID_VERSIONS)
    return valid

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

  def _Get_servo_v4_dts_mode(self):
    """Getter of servo_v4_dts_mode.

    Returns:
      "off": DTS mode is disabled.
      "on": DTS mode is enabled.
    """
    # Get the current DTS mode
    result = self._issue_cmd_get_results('dts', ['dts mode:\s*(off|on)'])[0]
    if result is None:
      raise ec3poServoV4Error('Cannot retrieve dts mode from console.')
    return result[1]

  def _Set_servo_v4_dts_mode(self, value):
    """Setter of servo_v4_dts_mode.

    Args:
      value: "off", "on"
    """
    if value == 'off' or value == 'on':
      self._issue_cmd('dts %s' % value)
    else:
      raise ValueError("Invalid dts_mode setting: '%s'. Try one of "
                       "'on' or 'off'." % value)

  def _get_pd_info(self, port):
    """Get the current PD state

    Args:
      port: Type C PD port 0/1
    Returns:
      "src|snk" for role  and state value
    """
    pd_cmd = 'pd %s state' % port
    # Two FW versions for this command, get full line.
    m = self._issue_cmd_get_results(pd_cmd, ['State:\s+([\w]+)_([\w]+)'])[0]
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
    pd = self._get_pd_info(self.DUT_PORT)
    return pd['role']

  def _Set_servo_v4_power_role(self, role):
    """Setter of servo_v4_role.

    This method is used to set the PD power role to the desired value. The
    power role is changed by executing a 'pd <port> swap power' console
    command. This requires that the DUT port be in an explicit contract
    (i.e. SRC_READY or SNK_READY state).
    Args:
      role: src, snk
    """
    role = role.lower()
    if role != 'src' and role != 'snk':
      raise ValueError("Invalid power role: '%s'. Try one of "
                       "'snk' or 'src'." % role)

    # Get current power role and state
    pd = self._get_pd_info(self.DUT_PORT)
    # If not in desired role and connected, then issue role swap
    if pd['role'] != role and pd['state'] == 'ready':
      # Send pd power role swap command
      self._issue_cmd('pd %s swap power' % self.DUT_PORT)
      # Give a little time for role swap to complete
      time.sleep(self.SWAP_DELAY)
      pd_new = self._get_pd_info(self.DUT_PORT)
      # Check if power role swap completed
      if pd_new['state'] != 'ready' or pd['role'] == pd_new['role']:
        raise ec3poServoV4Error('Power role swap failed')

  def _Get_servo_v4_ccd_keepalive(self):
    """Get keepalive status.

    Returns:
       1 if keepalive is enabled, 0 if it's not.
    """
    _, status = self._issue_cmd_get_results('keepalive',
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
