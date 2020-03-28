# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import hw_driver


class macro(hw_driver.HwDriver):
  """A special driver to implement virtual controls by macro.

  This driver allows defining new states by parameters, in format
  `set_value_${value}`. For example, a state 'on' is defined by parameter name
  'set_value_on'. Its value should be a list of controls to set, in
  `${control}:${state}` format. For example, 'spi2_verf:pp1800 spi_buf_en:on'.

  If parameter 'get_value' is set, the value must be a list of controls that
  will be evaluated to decide final state. This can be useful if you must ignore
  few write-only controls. If 'get_value' is not set, it will default to the
  list of all controls in 'set_value_*' parameters.
  """

  _STATE_UNKNOWN = 'unknown'

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(macro, self).__init__(interface, params)
    str_prefix = 'set_value_'

    def build_sequence(value):
      """Parse a string with multiple ${control}:${state} into list of tuple."""
      return list(k.split(':', 1) for k in value.split())

    self._states = dict((k[len(str_prefix):], build_sequence(v))
                        for k, v in self._params.items()
                        if k.startswith(str_prefix))
    all_controls = ' '.join(set(name for rule in self._states.values()
                                for name in map(lambda x: x[0], rule)))
    self._get_list = self._params.get('get_value', all_controls).split()

  def _has_control(self, control):
    """Returns True if control is available in current interface."""
    return self._interface._syscfg.is_control(control)

  def set(self, new_state):
    """Transit to a new state."""
    state_name = str(new_state)
    if state_name not in self._states:
      raise hw_driver.HwDriverError("Invalid state: '%s'. Supported states: %r"
                                    % (state_name, self._states.keys()))

    for control, state in self._states[state_name]:
      if not self._has_control(control):
        logging.warning("Ignore setting non-exist control '%s' to '%s'.",
                        control, state)
        continue
      # TODO(hungte) Support more commands like sleep(ms).
      self._interface.set(control, state)

  def get(self):
    """Checks and returns current state."""
    if not self._get_list:
      return self._STATE_UNKNOWN

    cached = {}
    def get_value(ctrl):
      if ctrl in cached:
        return cached[ctrl]
      value = self._interface.get(ctrl)
      cached[ctrl] = value
      return value

    for name, rules in self._states.items():
      # 'rules' is a list of (control, state) tuples.
      # To match, at least one control must be in self._get_list.
      matched = 0
      for control, state in rules:
        if control not in self._get_list or not self._has_control(control):
          continue
        if get_value(control) != state:
          break
        matched += 1
      else:
        if matched:
          return name

    return self._STATE_UNKNOWN
