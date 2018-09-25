# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for SystemConfig."""

import unittest

import system_config


class TestSystemConfig(unittest.TestCase):
  """Unittests for SystemConfig class behavior."""
  # pylint: disable=invalid-name
  # ALLOWABLE_INPUT_TYPES is defined in system_config module

  def setUp(self):
    """Set up a SystemConfig object to use. Cache module values."""
    super(TestSystemConfig, self).setUp()
    self.syscfg = system_config.SystemConfig()
    self.ALLOWABLE_INPUT_TYPES = system_config.ALLOWABLE_INPUT_TYPES

  def tearDown(self):
    """Restore module values."""
    system_config.ALLOWABLE_INPUT_TYPES = self.ALLOWABLE_INPUT_TYPES
    super(TestSystemConfig, self).tearDown()

  def _AddMap(self, map_name, params):
    """Helper to add a map to the SystemConfig."""
    self.syscfg.syscfg_dict['map'][map_name] = {'map_params': params}

  def test_ResolveValStandardInt(self):
    """A string containing an int gets returned as an int."""
    input_str = '1'
    # Empty dictionary is passing empty params.
    self.assertEqual(int(input_str), self.syscfg.resolve_val({}, input_str))

  def test_ResolveValStandardFloat(self):
    """A string containing a float gets returned as a float."""
    input_str = '1.1'
    # Empty dictionary is passing empty params.
    self.assertEqual(float(input_str), self.syscfg.resolve_val({}, input_str))

  def test_ResolveValMappedIntNotUsingMap(self):
    """A mapped control allows for raw input when the map is not used."""
    map_key = 'mapped_int'
    map_val = '1'
    map_name = 'sample_map'
    map_params = {map_key: map_val}
    self._AddMap(map_name, map_params)
    # These are the params from the control using the map. In this case they
    # need to include the map name.
    control_params = {'map': map_name}
    # The control is being set with 7, a raw input that is valid & does not
    # use the map.
    self.assertEqual(7, self.syscfg.resolve_val(control_params, 7))

  def test_ResolveValMappedInt(self):
    """A mapped integer value gets returned as its mapped integer value."""
    map_key = 'mapped_int'
    map_val = '1'
    map_name = 'sample_map'
    map_params = {map_key: map_val}
    self._AddMap(map_name, map_params)
    # These are the params from the control using the map. In this case they
    # need to include the map name.
    control_params = {'map': map_name}
    self.assertEqual(int(map_val), self.syscfg.resolve_val(control_params,
                                                           map_key))

  def test_ResolveValMappedFloat(self):
    """A mapped float value gets returned as its mapped float value."""
    map_key = 'mapped_float'
    map_val = '1.1'
    map_name = 'sample_map'
    map_params = {map_key: map_val}
    self._AddMap(map_name, map_params)
    # These are the params from the control using the map. In this case they
    # need to include the map name.
    control_params = {'map': map_name}
    self.assertEqual(float(map_val), self.syscfg.resolve_val(control_params,
                                                             map_key))

  def test_ResolveValMapNonExistant(self):
    """A non-existant map raises a SystemConfigError."""
    fake_map_name = 'fake_map'
    control_params = {'map': fake_map_name}
    with self.assertRaisesRegexp(system_config.SystemConfigError,
                                 "Map %s isn't defined" % fake_map_name):
      # 'random_key' passed as key as the key does not matter for this test.
      self.syscfg.resolve_val(control_params, 'random_key')

  def test_ResolveValMapKeyNonExistant(self):
    """A non-existant map key raises a SystemConfigError."""
    map_key = 'mapped_float'
    map_val = '1.1'
    map_name = 'sample_map'
    map_params = {map_key: map_val}
    self._AddMap(map_name, map_params)
    fake_map_key = 'fake_mapped_float'
    # These are the params from the control using the map. In this case they
    # need to include the map name.
    control_params = {'map': map_name}
    with self.assertRaisesRegexp(system_config.SystemConfigError,
                                 "Map %r doesn't contain "
                                 'key %r' % (map_name, fake_map_key)):
      self.syscfg.resolve_val(control_params, fake_map_key)

  def test_ResolveValInputType(self):
    """Each input type in |ALLOWABLE_INPUT_TYPES| gets returned properly."""
    # The input types are str, float, and int. Sample is int which can be all
    # 3
    raw_input_str = '1'
    # in setUp, ALLOWABLE_INPUT_TYPES get cached in self.
    for input_type, transform in self.ALLOWABLE_INPUT_TYPES.iteritems():
      # These are the params from the control using the map. In this case they
      # need to include the input type.
      control_params = {'input_type': input_type}
      resolved_val = self.syscfg.resolve_val(control_params, raw_input_str)
      expected_resolved_val = transform(raw_input_str)
      # Ensure they have the same value.
      self.assertEqual(expected_resolved_val, resolved_val)
      # Ensure they have the same type.
      self.assertEqual(type(expected_resolved_val), type(resolved_val))

  def test_ResolveValInputTypeInvalid(self):
    """Invalid input_type does not raise an error, does normal conversion."""
    system_config.ALLOWABLE_INPUT_TYPES = {}
    control_params = {'input_type': 'int'}
    input_val = expected_resolved_val = 1
    # Casting to string to verify that it does normal flow of converting to int.
    resolved_val = self.syscfg.resolve_val(control_params, str(input_val))
    # Ensure they have the same value.
    self.assertEqual(expected_resolved_val, resolved_val)
    # Ensure they have the same type.
    self.assertEqual(type(expected_resolved_val), type(resolved_val))

  def test_ResolveValMappedInputType(self):
    """A mapped value will also be transformed to the proper input type."""
    map_key = 'mapped_int'
    map_val = '1'
    map_name = 'sample_map'
    map_params = {map_key: map_val}
    self._AddMap(map_name, map_params)
    # These are the params from the control using the map. In this case they
    # need to include the map name, and the input_type.
    control_params = {'map': map_name,
                      'input_type': 'float'}
    expected_resolved_val = float(map_val)
    # First, the |map_key| is converted to |map_val| i.e. '1'.
    # Second, input_type 'float' means resolve returns float('1')
    resolved_val = self.syscfg.resolve_val(control_params, map_key)
    # Ensure they have the same value.
    self.assertEqual(expected_resolved_val, resolved_val)
    # Ensure they have the same type.
    self.assertEqual(type(expected_resolved_val), type(resolved_val))

if __name__ == '__main__':
  unittest.main()
