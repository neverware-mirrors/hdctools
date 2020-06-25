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

  def _AddNAControl(self, name, extra_params={}):
    # pylint: disable=dangerous-default-value
    """Helper to add an 'N/A' control to the SystemConfig.

    Add control |name| with some default params:
      - drv: na
      - interface: na

    Args:
      name: control name
      extra_params: dict of extra parameters to add
    """
    base_params = {'drv': 'na',
                   'interface': 'na'}
    base_params.update(extra_params)
    control_entry = {'doc': '',
                     'get_params': base_params,
                     'set_params': base_params}
    self.syscfg.syscfg_dict[system_config.CONTROL_TAG][name] = control_entry

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
    for input_type, transform in self.ALLOWABLE_INPUT_TYPES.items():
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

  def test_TagsForTaggedControl(self):
    """Multiple tagged controls will be found using their tag."""
    tagged_controls = ['test1', 'test2', 'test3']
    tag = 'testtag'
    for control in tagged_controls:
      # Pass the tag in as extra params
      self._AddNAControl(control, {'tags': tag})
    self.syscfg.finalize()
    found_tagged_controls = self.syscfg.get_controls_for_tag(tag)
    # Assert that the same controls are found that were fed in.
    assert sorted(found_tagged_controls) == sorted(tagged_controls)

  def test_MultipleTagsForTaggedControl(self):
    """Multiple tagged controls will be found using all their tag."""
    tagged_controls = ['test1', 'test2', 'test3']
    tags = 'testtag, testtag2'
    for control in tagged_controls:
      self._AddNAControl(control, {'tags': tags})
    self.syscfg.finalize()
    # Split tags into individual tags using helper.
    for tag in system_config.SystemConfig.tag_string_to_tags(tags):
      found_tagged_controls = self.syscfg.get_controls_for_tag(tag)
      # Assert that the same controls are found that were fed in.
      assert sorted(found_tagged_controls) == sorted(tagged_controls)

  def test_TagUnkown(self):
    """System returns an empty list if the tag is unknown."""
    tagged_controls = ['test1', 'test2', 'test3']
    tag = 'testtag'
    for control in tagged_controls:
      # Pass the tag in as extra params
      self._AddNAControl(control, {'tags': tag})
    self.syscfg.finalize()
    unknown_tag = 'unknown'
    found_tagged_controls = self.syscfg.get_controls_for_tag(unknown_tag)
    # Assert that no controls were found.
    assert not found_tagged_controls


if __name__ == '__main__':
  unittest.main()
