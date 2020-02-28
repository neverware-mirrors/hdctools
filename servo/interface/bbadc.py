# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allows creation of ADC interface for beaglebone devices."""
import glob
import os

import common as c
import interface


class BBadcError(c.InterfaceError):
  """Class for exceptions of BBadc."""

  def __init__(self, msg, value=0):
    """BBadc constructor.

    Args:
      msg: string, message describing error in detail
      value: integer, value of error when non-zero status returned.  Default=0
    """
    super(BBadcError, self).__init__(msg, value)
    self.msg = msg
    self.value = value


class BBadc(interface.Interface):
  """Provides interface to ADC through beaglebone."""

  ADC_ENABLE_COMMAND = 'echo cape-bone-iio > %s'
  ADC_ENABLE_NODE = '/sys/devices/bone_capemgr.*/slots'
  ADC_IN_NODE = '/sys/devices/ocp.*/helper.*/AIN*'

  def __init__(self):
    """Enables ADC drvier."""
    interface.Interface.__init__(self)
    adc_nodes = glob.glob(BBadc.ADC_ENABLE_NODE)
    for adc_node in adc_nodes:
      os.system(BBadc.ADC_ENABLE_COMMAND % adc_node)

  @staticmethod
  def Build(**kwargs):
    """Factory method to implement the interface."""
    return BBadc()

  @staticmethod
  def name():
    """Name to request interface by in interface config maps."""
    return 'bb_adc'

  def read(self):
    """Reads ADC values.

    Returns:
      ADC inputs from AIN0 to AIN7.
    """
    buffer = []
    adc_in_nodes = glob.glob(BBadc.ADC_IN_NODE)
    for adc_in in adc_in_nodes:
      with open(adc_in, 'r') as f:
        buffer.append(int(f.read(), 10))

    return buffer
