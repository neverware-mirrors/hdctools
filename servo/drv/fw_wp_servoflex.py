# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import fw_wp_state


class fwWpServoflex(fw_wp_state.FwWpStateDriver):
  """Driver for fw_wp_state for boards connecting servoflex's."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(fwWpServoflex, self).__init__(interface, params)
    self._fw_wp_vref = self._params.get('fw_wp_vref', 'pp1800')

    # Get the control prefix, like 'hammer_', if it is a base control.
    control_name = self._params.get('control_name', '')
    assert control_name.endswith('fw_wp_state'), 'Should be fw_wp_state control'
    self._prefix = control_name.replace('fw_wp_state', '')

  def _interface_get(self, control):
    """Get the value of the given control with proper prefix."""
    return self._interface.get(self._prefix + control)

  def _interface_set(self, control, value):
    """Set the value of the given control with proper prefix."""
    return self._interface.set(self._prefix + control, value)

  def _force_on(self):
    """Force the firmware to write-protected."""
    self._interface_set('fw_wp_vref', self._fw_wp_vref)
    self._interface_set('fw_wp_en', 'on')
    self._interface_set('fw_wp', 'on')

  def _force_off(self):
    """Force the firmware to not write-protected."""
    self._interface_set('fw_wp_vref', self._fw_wp_vref)
    self._interface_set('fw_wp_en', 'on')
    self._interface_set('fw_wp', 'off')

  def _reset(self):
    """Reset the firmware write-protection state to the system value."""
    self._interface_set('fw_wp_en', 'off')

  def _get_state(self):
    """Get the firmware write-protection state."""
    fw_wp_en = (self._interface_get('fw_wp_en') == 'on')
    fw_wp = (self._interface_get('fw_wp') == 'on')
    if fw_wp_en:
      return self._STATE_FORCE_ON if fw_wp else self._STATE_FORCE_OFF
    else:
      return self._STATE_ON if fw_wp else self._STATE_OFF
