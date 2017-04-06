# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servo v4 specific controls through ec3po.

Provides the following console controlled function subtypes:
  servo_v4_ccd_mode
"""

import logging

import pty_driver
import servo


# EC console mask for enabling only command channel
COMMAND_CHANNEL_MASK = 0x1

# Controls to set in batch operations.
# [usbsnk, ccd, rpusb, rpchg, disconnect, usbchg]
ccd_typec_config = {
  "DUT_CHG_EN":         ("0", "0", "1", "1", "0", "1"),
  "HOST_OR_CHG_CTL":    ("0", "0", "0", "1", "0", "1"),
  "USB_DUT_CC1_RD":     ("0", "0", "IN", "IN", "IN", "IN"),
  "USB_DUT_CC2_RD":     ("IN", "0", "IN", "IN", "IN", "IN"),
  "USB_DUT_CC1_RPUSB":  ("IN", "IN", "1", "1", "IN", "IN"),
  "USB_DUT_CC2_RP1A5":  ("IN", "IN", "1", "1", "IN", "IN"),
  "USB_DUT_CC1_RP3A0":  ("IN", "IN", "IN", "IN", "IN", "1"),
}



class ec3poServoV4Error(Exception):
  """Exception class."""


class ec3poServoV4(pty_driver.ptyDriver):
  """Object to access drv=ec3po_servo_v4 controls.

  Note, instances of this object get dispatched via base class,
  HwDriver's get/set method. That method ultimately calls:
    "_[GS]et_%s" % params['subtype'] below.
  """

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

    if "console" in params:
      if params["console"] == "enhanced" and \
          type(interface) is servo.ec3po_interface.EC3PO:
        interface._console.oobm_queue.put('interrogate never enhanced')
      else:
        raise ec3poServoV4Error("Enhanced console must be ec3po!")

    self._logger.debug("")

  def batch_set(self, batch, index):
    """Set a batch of values on console gpio.

    Args:
      batch: dict of GPIO names, and on/off value
      index: index of batch preset
    """
    if index not in range(len(batch.values()[0])):
      raise ec3poServoV4Error("Index %s out of range" % index)

    cmds = []
    for name, values in batch.items():
      cmds.append("gpioset %s %s\r" % (name, values[index]))

    self._issue_cmd(cmds)


  def _Set_ccvalues(self, value):
    """Set or unset CC lines to indicate CCD

    Args:
      value: An integer value, see "servo_v4_cc_map"
    """
    self.batch_set(ccd_typec_config, value)

  def _Get_servo_v4_dts_mode(self):
    """Getter of servo_v4_dts_mode.

    Returns:
      "off": DTS mode is disabled.
      "on": DTS mode is enabled.
    """
    # Get the current DTS mode
    result = self._issue_cmd_get_results(
        "dts", ["dts mode:\s*(off|on)"])[0]
    if result is None:
      raise ec3poServoV4Error("Cannot retrieve dts mode from console.")
    return result[1]

  def _Set_servo_v4_dts_mode(self, value):
    """Setter of servo_v4_dts_mode.

    Args:
      value: "off", "on"
    """
    if value == "off" or value == "on":
      self._issue_cmd("dts %s" % value)
    else:
      raise ValueError("Invalid dts_mode setting: '%s'. Try one of "
                       "'on' or 'off'." % value)
