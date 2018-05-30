# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test collection to verify integrity of servod configuration files."""

from __future__ import print_function
import collections
import glob
import os
import xml.etree.ElementTree

import pytest

# pylint: disable=invalid-name
# py.test conventions make consistent naming difficult.

# module wide data needed for all tests.
dataindex = None


# TODO(coconutruben): This test should really run through the setup.py building
# of the servo.data package before running, locally to ensure that all files are
# generated.

class DataIndex(object):
  """Index of servod configurations to make subsequent testing easier.

  The index is a dictionary, where each key is one of the three config entry
  types: 'control' 'map' and 'include'.
  Under each key, is a list containing a parsed version of each config entry.
  This 'parse version' is a dictionary, where each key a subelement found under
  the entry in the XML. The value is a list, containing all the sub-element
  texts. The one difference is 'params' where the list doesn't contain the texts
  but rather the attributes for the params.
  Lastly, the extra key 'cfgname' is set to the name of the config file the
  entry came from - for debugging.

  Example:
    In the XML config:                In the index:
    <control>                         { 'name': ['test_ctr'],
      <name>test_ctr</name>             'params': [{a:1,b:2}, {a:2, b:7}]
      <params a=1 b=2></params>         'doc': ['doc for test'] }
      <params a=2 b=7></params>
      <doc>doc for test</doc>
    </control>

  Attributes:
    cfg_file_pattern: pattern to use when enumerating all servod config files.
    cfg_names: a set of all configuration files.
    _cfg_tags: actual index.
    _servo_data_dir: directory to search for servod configurations.
  """

  cfg_file_pattern = '*.xml'

  def _LoadCfgs(self):
    """Parse XML configurations and turn into index format described above."""
    self._cfg_files = glob.glob(os.path.join(self._servo_data_dir,
                                             self.cfg_file_pattern))
    for cfg_file in self._cfg_files:
      cfgname = os.path.basename(cfg_file)
      cfg = xml.etree.ElementTree.parse(cfg_file).getroot()
      for cfgtag in ['control', 'map', 'include']:
        for element in cfg.findall(cfgtag):
          elem = collections.defaultdict(list)
          elem['cfgsource'] = cfgname
          self.cfg_names.add(cfgname)
          for subelement in element.findall('*'):
            if subelement.tag == 'params':
              elem[subelement.tag].append(subelement.attrib)
            else:
              elem[subelement.tag].append(subelement.text)
          self._cfg_tags[cfgtag].append(elem)

  def __init__(self, servo_data_dir):
    """Init the index by loading and parsing all configurations.

    Args:
      servo_data_dir: directory containing all the servod configuration files.
    """
    self.cfg_names = set()
    self._servo_data_dir = servo_data_dir
    self._cfg_tags = collections.defaultdict(list)
    self._LoadCfgs()

  def GetControls(self):
    """Return list of all control elements found."""
    return self._cfg_tags['control']

  def GetControlsWithAttribute(self, attribute):
    """Return a list of controls with |attribute| in at least one params.

    Args:
      attribute: attribute to search for in control's params element

    Returns:
      list of control dictionaries with |attribute| in at least one params
    """
    ctrls = self.GetControls()
    attrib_ctrls = []
    for ctrl in ctrls:
      for param in ctrl['params']:
        if attribute in param:
          attrib_ctrls.append(ctrl)
          # if there are two params and they both have it, only add ctrl once
          break
    return attrib_ctrls

  def GetMaps(self):
    """Return list of all maps elements found."""
    return self._cfg_tags['map']

  def GetIncludes(self):
    """Return list of all include elements found."""
    return self._cfg_tags['include']


def IndexData(servo_data_dir):
  """Initialize data index once.

  Args:
    servo_data_dir: directory to look for servod config files.

  Returns:
    dataindex: a reference to the global dataindex
  """
  # pylint: disable=global-statement
  global dataindex
  if not dataindex:
    dataindex = DataIndex(servo_data_dir)
  return dataindex


def pytest_generate_tests(metafunc):
  """Generate parameterized tests using the dataindex.

  Args:
    metafunc: pytest metafunc object to inspect what test method/class
              the function is currently generating tests for.
  """
  index = IndexData(os.path.dirname(__file__))
  if metafunc.cls == TestControlIntegrity:
    # generate a test-control integrity tests for all controls
    metafunc.parametrize('control', index.GetControls())
  if metafunc.cls == TestMapIntegrity:
    # generate map integrity tests for all maps
    metafunc.parametrize('m', index.GetMaps())
    # generate include integrity tests for all includes
  if metafunc.cls == TestIncludeIntegrity:
    metafunc.parametrize('include', index.GetIncludes())
  if metafunc.cls == TestEcosystemIntegrity:
    if 'map_control' in metafunc.fixturenames:
      metafunc.parametrize('map_control',
                           index.GetControlsWithAttribute('map'))
    if 'include' in metafunc.fixturenames:
      metafunc.parametrize('include', index.GetIncludes())


@pytest.fixture(scope='module')
def cfg_files():
  """Helper to list all servod config files available.

  Returns:
    a set of servod config files found
  """
  index = IndexData(os.path.dirname(__file__))
  return index.cfg_names


@pytest.fixture(scope='module')
def defined_maps():
  """Helper to list all maps defined in servod available.

  Returns:
    set of all maps defined in servod config files
  """
  index = IndexData(os.path.dirname(__file__))
  maps = set()
  map_elems = index.GetMaps()
  for map_elem in map_elems:
    maps.add(map_elem['name'][0])
  return maps


class TestEcosystemIntegrity(object):
  """Test that cross-references in the configurations are sound."""

  def test_AllUsedMapsExist(self, map_control, defined_maps):
    """Verify that a used map is defined somewhere.

    Args:
      map_control: dictionary containing a map control
      defined_maps: set of all maps defined by servod config files
    """
    # pylint: disable=redefined-outer-name
    for param in map_control['params']:
      if 'map' in param:
        assert param['map'] in defined_maps

  def test_AllIncludesExist(self, include, cfg_files):
    """Verify that all includes actually exist on the system."""
    # pylint: disable=redefined-outer-name
    assert include['name'][0] in cfg_files


class TestIncludeIntegrity(object):
  """Test all included configurations exist."""

  @pytest.fixture(scope='class', params=[('name', 1)])
  def element(self, request):
    """Helper to parameterize over all map components: name, doc and params.

    Args:
      request: pytest request object identifying what test-method is requesting

    Returns:
      param: a tuple, with name of the param at param[0] required number of
             occurrences in param[1]
    """
    return request.param

  def test_IncludeElement(self, include, element):
    """|element|[0] is in |include| one of |element|[1] number of times.

    Args:
      include: dictionary containing all include elements
      element: tuple where element[0] is the element name and element[1] is a
               tuple containing all acceptable numbers of that element showing
               up in a include
    """
    num_expected = element[1]
    element_vals = include[element[0]]
    assert len(element_vals) == num_expected


class TestMapIntegrity(object):
  """Test all maps have a name, a param, and at most one doc string."""

  @pytest.fixture(scope='class', params=[('name', (1,)),
                                         ('doc', (0, 1)),
                                         ('params', (1,))])
  def element(self, request):
    """Helper to parameterize over all map components: name, doc and params.

    Args:
      request: pytest request object identifying what test-method is requesting

    Returns:
      param: a tuple, with name of the param at param[0] and all allowable
             number of occurances of this param in a map at param[1]
    """
    return request.param

  def test_MapElement(self, m, element):
    """|element|[0] is in |m| one of |element|[1] number of times.

    Args:
      m: dictionary containing map elements
      element: tuple where element[0] is the element name and element[1] is a
               tuple containing all acceptable numbers of that element showing
               up in a map
    """
    num_expected = element[1]
    element_vals = m[element[0]]
    assert len(element_vals) in num_expected


@pytest.fixture(scope='module')
def servo_drvs(drvdir=os.path.join(os.path.dirname(__file__), '..', 'drv')):
  """Helper to list all servod driver files available."""
  return os.listdir(drvdir)


class TestControlIntegrity(object):
  """Tests to verify individual controls are valid."""

  @pytest.fixture(scope='class', params=[('name', (1,)),
                                         ('doc', (0, 1)),
                                         ('params', (1, 2)),
                                         ('alias', (0, 1)),
                                         ('remap', (0, 1))])
  def element(self, request):
    """Helper to parameterize over all control components.

    Args:
      request: pytest request object identifying what test-method is requesting

    Returns:
      param: a tuple, with name of the param at param[0] and all allowable
             number of occurances of this param in a control at param[1]
    """
    return request.param

  @pytest.fixture(scope='class', params=['drv', 'interface'])
  def param_attrib(self, request):
    """Helper to parameterize over required param attributes: drv & interface.

    Args:
      request: pytest request object identifying what test-method is requesting

    Returns:
      param: either 'drv' or 'interface'
    """
    return request.param

  def test_ControlElement(self, control, element):
    """|element|[0] is in |control| one of |element|[1] number of times.

    Args:
      control: dictionary with control elements
      element: tuple where element[0] is the element name and element[1] is a
               tuple containing all acceptable numbers of that element showing
               up in a control
    """
    if 'remap' in control:
      pytest.skip('remap controls do not use all elements.')
    num_expected = element[1]
    element_vals = control[element[0]]
    assert len(element_vals) in num_expected

  def test_ParamIntegrity(self, control, param_attrib):
    """Verify required param attributes.

    Args:
      control: dictionary with control elements
      param_attrib: required attribute for a control param. Either 'drv' or
                   'interface'
    """
    for param in control['params']:
      if 'clobber_ok' in param:
        pytest.skip('clobber_ok controls are update controls, and do not '
                    'require all elements of a full control.')
      if 'remap' in control:
        pytest.skip('remap controls do not use all elements.')
      assert param_attrib in param

  def test_DoubleParams(self, control):
    """Verify on two params controls that there's cmd='set' and cmd='get'.

    Args:
      control: dictionary with control elements.
    """
    if len(control['params']) != 2:
      pytest.skip('DoubleParams test only applies to controls with two params.')
    cmds = set([param['cmd'] for param in control['params']])
    assert cmds == set(['set', 'get'])

  def test_DrvAvailability(self, control, servo_drvs):
    """Verify drv attribute exists.

    Args:
      control: dictionary with control elements
      servo_drvs: list of all servo drv modules
    """
    # pylint: disable=redefined-outer-name
    for param in control['params']:
      if 'drv' not in param:
        pytest.skip('DrvAvailability does not apply if no driver defined.')
      drv = param['drv']
      drvfile = '%s.py' % drv
      assert drvfile in servo_drvs
