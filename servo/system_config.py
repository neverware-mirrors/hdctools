# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""System configuration module."""
import collections
import glob
import logging
import os
import re
import xml.etree.ElementTree

# valid tags in system config xml.  Any others will be ignored
SYSCFG_TAG_LIST = ['map', 'control']
ALLOWABLE_INPUT_TYPES = {'float': float, 'int': int, 'str': str}


# pylint: disable=g-bad-exception-name
# TODO(coconutruben): figure out if it's worth it to rename this so that it
# removes the 'stutter'
class SystemConfigError(Exception):
  """Error class for SystemConfig."""


class SystemConfig(object):
  """SystemConfig Class.

  System config files describe how to talk to various pieces on the device under
  test.  The system config may be broken up into multiple file to make it easier
  to share configs among similar DUTs.  This class has the support to take in
  multiple SystemConfig files and treat them as one unified structure


  SystemConfig files are written in xml and consist of four main elements

  0. Include : Ability to include other config files

  <include>
    <name>servo_loc.xml</name>
  </include>

  NOTE, All includes in a file WILL be sourced prior to any other elements in
  the XML.

  1. Map : Allow user-friendly naming for things to abstract
  certain things like on=0 for things that are assertive low on
  actual h/w

  <map>
    <name>onoff_i</name>
    <doc>assertive low map for on/off</doc>
    <params on="0" off="1"></params>
  </map>

  2. Control : Bulk of the system file.  These elements are
  typically gpios, adcs, dacs which allow either control or sampling
  of events on the h/w. Controls should have a 1to1 correspondence
  with hardware elements between control system and DUT.

  <control>
    <name>warm_reset</name>
    <doc>Reset the device warmly</doc>
    <params interface="1" drv="gpio" offset="5" map="onoff_i"></params>
  </control>


  TODO(tbroch) Implement sequence or deprecate
  3. Sequence : List of control calls to create a desired
  configuration of h/w.  These could certainly be done by writing
  simple scripts to send individual control calls to the server but
  encapsulating them into the system file should allow for tighter
  control of the sequence ... especially if timing of the sequence
  is paramount.

  <sequence>
    <name>i2c_mux_seq</name>
    <cmdlist>i2c_mux_en:off i2c_mux_add:__arg0__ i2c_mux_en:on</cmdlist>
  </sequence>

  Public Attributes:
    syscfg_dict: 3-deep dictionary created when parsing system files.  Its
        organized as [tag][name][type] where:
        tag: map | control | sequence
        name: string name of tag element
        type: data type of payload either, doc | get | set presently
          doc: string describing the map,control or sequence
          get: a dictionary for getting values from named control
          set: a dictionary for setting values to named control
    hwinit: list of control tuples (name, value) to be initialized in order

  Private Attributes:
    _loaded_xml_files: set of filenames already loaded to avoid sourcing XML
      multiple times.
  """

  def __init__(self):
    """SystemConfig constructor."""
    self._logger = logging.getLogger('SystemConfig')
    self._logger.debug('')
    self.syscfg_dict = collections.defaultdict(dict)
    self.hwinit = []
    self._loaded_xml_files = []
    self._board_cfg = None

  def find_cfg_file(self, filename):
    """Find the filename for a system XML config file.

    If the provided `filename` names a valid file, use that.
    Otherwise, `filename` must name a file in the 'data'
    subdirectory stored with this module.

    Returns the path selected as described above; if neither of the
    paths names a valid file, return `None`.

    Args:
      filename: string of path to system file ( xml )

    Returns:
      string full path of |filename| if it exists, otherwise None
    """
    if os.path.isfile(filename):
      return filename
    default_path = os.path.join(os.path.dirname(__file__), 'data')
    fullname = os.path.join(default_path, filename)
    if os.path.isfile(fullname):
      return fullname
    return None

  def get_all_cfg_names(self):
    """Return all XML config file names.

    Returns:
      A list of file names.
    """
    exclude_re = re.compile(r'servo_.*_overlay\.xml')
    pattern = os.path.join(os.path.dirname(__file__), 'data', '*.xml')

    cfg_names = []
    for name in glob.glob(pattern):
      name = os.path.basename(name)
      if not exclude_re.match(name):
        cfg_names.append(name)
    return cfg_names

  def set_board_cfg(self, filename):
    """Save the filename for the board config."""
    self._board_cfg = filename

  def get_board_cfg(self):
    """Return the board filename."""
    return self._board_cfg

  def add_cfg_file(self, filename, name_prefix=None, interface_increment=0):
    """Add system config file to the system config object.

    Each design may rely on multiple system files so need to have the facility
    to parse them all.

    For example, we may have a:
    1. default for all controls that are the same for each of the
    control systems
    2. default for a particular DUT system's usage across the
    connector
    3. specific one for particular version of DUT (evt,dvt,mp)
    4. specific one for a one-off rework done to a system

    Special key parameters in config files:
      clobber_ok: signifies this control may _clobber_ an existing definition
        of the same name.  Note, its value is ignored ( clobber_ok='' )

    NOTE, method is recursive when parsing 'include' elements from XML.

    The arguments name_prefix and interface_increment are used to support
    multiple servo micros. The interfaces of the extra servo micros, like
    the one for hammer, are relocated to higher slots. The controls of this
    extra servo micros should be shifted their interface numbers. Adding
    the name prefix avoid conflict with the main servo micro.

    Args:
      filename: string of path to system file ( xml )
      name_prefix: string to prepend to all control names
      interface_increment: number to add to all interfaces

    Raises:
      SystemConfigError: for schema violations, or file not found.
    """
    cfgname = self.find_cfg_file(filename)
    if not cfgname:
      msg = 'Unable to find system file %s' % filename
      self._logger.error(msg)
      raise SystemConfigError(msg)

    filename = cfgname
    if (filename, name_prefix, interface_increment) in self._loaded_xml_files:
      self._logger.warn('Already sourced system file (%s, %s, %d).', filename,
                        name_prefix, interface_increment)
      return
    self._loaded_xml_files.append((filename, name_prefix, interface_increment))

    self._logger.info('Loading XML config (%s, %s, %d)', filename, name_prefix,
                      interface_increment)
    root = xml.etree.ElementTree.parse(filename).getroot()
    for element in root.findall('include'):
      self.add_cfg_file(
          element.find('name').text, name_prefix, interface_increment)
    for tag in SYSCFG_TAG_LIST:
      for element in root.findall(tag):
        element_str = xml.etree.ElementTree.tostring(element)
        try:
          name = element.find('name').text
          if tag == 'control' and name_prefix:
            name = name_prefix + name
        except AttributeError:
          # TODO(tbroch) would rather have lineno but dumping element seems
          # better than nothing.  Utimately a DTD/XSD for the XML schema will
          # catch these anyways.
          raise SystemConfigError('%s: no name ... see XML\n%s' % (tag,
                                                                   element_str))
        try:
          doc = ' '.join(element.find('doc').text.split())
        except AttributeError:
          doc = 'undocumented'
        try:
          alias = element.find('alias').text
        except AttributeError:
          alias = None
        try:
          remap = element.find('remap').text
        except AttributeError:
          remap = None

        if remap:
          try:
            self.syscfg_dict[tag][remap] = self.syscfg_dict[tag][name]
          except KeyError:
            # Sometimes the remap control doesn't exist (e.g. fw_up in servo
            # v4).  Just ignore it and continue on.
            pass
          continue

        get_dict = None
        set_dict = None
        clobber_ok = False
        params_list = element.findall('params')

        # Modify the interface attributes.
        for params in params_list:
          if 'interface' in params.attrib:
            if params.attrib['interface'] != 'servo':
              interface_id = int(params.attrib['interface'])
              params.attrib['interface'] = interface_id + interface_increment

        if len(params_list) == 2:
          assert tag != 'map', 'maps have only one params entry'
          for params in params_list:
            if 'cmd' not in params.attrib:
              raise SystemConfigError('%s %s multiple params but no cmd\n%s' %
                                      (tag, name, element_str))
            cmd = params.attrib['cmd']
            if cmd == 'get':
              if get_dict:
                raise SystemConfigError(
                    '%s %s multiple get params defined\n%s' % (tag, name,
                                                               element_str))
              get_dict = params.attrib
            elif cmd == 'set':
              if set_dict:
                raise SystemConfigError(
                    '%s %s multiple set params defined\n%s' % (tag, name,
                                                               element_str))
              set_dict = params.attrib
            else:
              raise SystemConfigError("%s %s cmd of 'get'|'set' not found\n%s" %
                                      (tag, name, element_str))
        elif len(params_list) == 1:
          get_dict = params_list[0].attrib
          set_dict = get_dict
        else:
          raise SystemConfigError('%s %s has illegal number of params %d\n%s' %
                                  (tag, name, len(params_list), element_str))

        # Save the control name to the params dicts, such that the driver can
        # refer to it.
        if tag == 'control':
          get_dict['control_name'] = name
          set_dict['control_name'] = name

        clobber_ok = ('clobber_ok' in set_dict or 'clobber_ok' in get_dict)
        if (tag == 'control' and name in self.syscfg_dict[tag] and
            not clobber_ok):
          raise SystemConfigError(
              "Duplicate %s %s without 'clobber_ok' key\n%s" % (tag, name,
                                                                element_str))

        if tag == 'map':
          self.syscfg_dict[tag][name] = {'doc': doc, 'map_params': get_dict}
          if alias:
            raise SystemConfigError('No aliases for maps allowed')
          continue

        if 'init' in set_dict:
          hwinit_found = False
          # only allow one hwinit per control
          if clobber_ok:
            for i, (hwinit_name, _) in enumerate(self.hwinit):
              if hwinit_name == name:
                self.hwinit[i] = (name, set_dict['init'])
                hwinit_found = True
                break

          if not hwinit_found:
            self.hwinit.append((name, set_dict['init']))

        if clobber_ok and name in self.syscfg_dict[tag]:
          # it's an existing control
          self.syscfg_dict[tag][name]['get_params'].update(get_dict)
          self.syscfg_dict[tag][name]['set_params'].update(set_dict)
          if doc != 'undocumented':
            self.syscfg_dict[tag][name]['doc'] = doc
        else:
          # it's a new control
          self.syscfg_dict[tag][name] = {
              'doc': doc,
              'get_params': get_dict,
              'set_params': set_dict
          }
        if alias:
          for aliasname in (elem.strip() for elem in alias.split(',')):
            if name_prefix:
              aliasname = name_prefix + aliasname
            self.syscfg_dict[tag][aliasname] = self.syscfg_dict[tag][name]

  def lookup_control_params(self, name, is_get=True):
    """Lookup & return control parameter dictionary.

    Note, controls must have either one or two set of parameters.  In the case
    of two, the dictionary must contain k=v element of 'type':'get' or
    'type':'set'

    Args:
      name: string of control name to lookup
      is_get: boolean of whether params should be for 'get' | 'set'

    Returns:
      control's parameter dictionary for approrpiate get or set

    Raises:
      NameError: if control name not found
      SystemConfigError: if error encountered identifying parameters
    """
    if name not in self.syscfg_dict['control']:
      raise NameError('No control named %s. All controls:\n%s' %
                      (name,
                       ','.join(sorted(self.syscfg_dict['control'].keys()))))
    if is_get:
      return self.syscfg_dict['control'][name]['get_params']
    else:
      return self.syscfg_dict['control'][name]['set_params']

  def is_control(self, name):
    """Determine if name is a control or not.

    Args:
      name: string of control name to lookup

    Returns:
      boolean, True if name is control, False otherwise
    """
    return name in self.syscfg_dict['control']

  def get_control_docstring(self, name):
    """Get controls doc string.

    Args:
      name: string of control name to lookup

    Returns:
      doc string of the control
    """
    return self.syscfg_dict['control'][name]['doc']

  def _lookup(self, tag, name_str):
    """Lookup the tag name_str and return dictionary or None if not found.

    Args:
      tag: string of tag (from SYSCFG_TAG_LIST) to look for name_str under.
      name_str: string of name to lookup

    Returns:
      dictionary from syscfg_dict[tag][name_str] or None
    """
    self._logger.debug('lookup of %s %s', tag, name_str)
    return self.syscfg_dict[tag].get(name_str)

  def resolve_val(self, params, map_vstr):
    """Resolve string value.

    Values to set the control to can be mapped to symbolic strings for better
    readability.  For example, its difficult to remember assertion levels of
    various gpios.  Maps allow things like 'reset:on'.  Also provides
    abstraction so that assertion level doesn't have to be exposed.

    Args:
      params: parameters dictionary for control
      map_vstr: string thats acceptable values are:
          an int (can be "DECIMAL", "0xHEX", 0OCT", or "0bBINARY".
          a floating point value.
          an alphanumeric which is key in the corresponding map dictionary.

    Returns:
      Resolved value as float or int or str depending on mapping & input type

    Raises:
      SystemConfigError: mapping issues found
    """
    # its a map
    err = 'Unknown error formatting input value.'
    if 'map' in params:
      map_dict = self._lookup('map', params['map'])
      if map_dict is None:
        raise SystemConfigError("Map %s isn't defined" % params['map'])
      try:
        map_vstr = map_dict['map_params'][map_vstr]
      except KeyError:
        # Do not raise error yet. This might just be that the input is not
        # using the map i.e. it's directly writing a raw mapped value.
        err = "Map '%s' doesn't contain key '%s'\n" % (params['map'], map_vstr)
        err += "Try one of -> '%s'" % "', '".join(map_dict['map_params'].keys())
    if 'input_type' in params:
      if params['input_type'] in ALLOWABLE_INPUT_TYPES:
        try:
          input_type = ALLOWABLE_INPUT_TYPES[params['input_type']]
          return input_type(map_vstr)
        except ValueError:
          err += "\n%s Input should be 'int' or 'float'." % ('Or' if 'Map' in
                                                             err else '')
      else:
        self._logger.error('Unrecognized input type.')
    # TODO(tbroch): deprecate below once all controls have input_type params
    try:
      return int(str(map_vstr), 0)
    except ValueError:
      pass
    try:
      return float(str(map_vstr))
    except ValueError:
      # No we know that nothing worked, and there was an error.
      raise SystemConfigError(err)

  # pylint: disable=invalid-name
  # Naming convention to dynamically find methods based on config parameter
  def _Fmt_hex(self, int_val):
    """Format integer into hex.

    Args:
      int_val: integer to be formatted into hex string

    Returns:
      string of integer in hex format
    """
    return hex(int_val)

  def reformat_val(self, params, value):
    """Reformat value.

    Formatting determined via:
      1. if has map, then remap
      2. else if has fmt param, use that function

    Args:
      params: parameter dictionary for control
      value: value to reformat

    Returns:
      formatted string value if reformatting needed
      value otherwise

    Raises:
      SystemConfigError: errors using formatting param
    """
    # TODO(crbug.com/841097): revisit logic for value here once
    # resolution found on bug.
    if value is not None and 'map' not in params and 'fmt' not in params:
      return value
    reformat_value = str(value)
    if 'map' in params:
      map_dict = self._lookup('map', params['map'])
      if map_dict:
        for keyname, val in map_dict['map_params'].iteritems():
          if val == reformat_value:
            reformat_value = keyname
            break
    elif 'fmt' in params:
      fmt = params['fmt']
      try:
        func = getattr(self, '_Fmt_%s' % fmt)
      except AttributeError:
        raise SystemConfigError('Unrecognized format %s' % fmt)
      try:
        reformat_value = func(value)
      except Exception:
        raise SystemConfigError('Problem executing format %s' % fmt)
    return reformat_value

  def display_config(self, tag=None, prefix=None):
    """Display human-readable values of map, control, or sequence.

    Args:
      tag  : string of either 'map' | 'control' | 'sequence' or None for all
      prefix: prefix string to print infront of control tags

    Returns:
      string to be displayed.
    """
    rsp = []
    if tag is None:
      tag_list = SYSCFG_TAG_LIST
    else:
      tag_list = [tag]
    for tag in sorted(tag_list):
      prefix_str = ''
      if tag == 'control' and prefix:
        prefix_str = '%s.' % prefix
      rsp.append('*************')
      rsp.append('* ' + tag.upper())
      rsp.append('*************')
      max_len = max(len(name) for name in self.syscfg_dict[tag].iterkeys())
      max_len += len(prefix_str)
      dashes = '-' * max_len
      for name in sorted(self.syscfg_dict[tag].iterkeys()):
        item_dict = self.syscfg_dict[tag][name]
        padded_name = '%-*s' % (max_len, '%s%s' % (prefix_str, name))
        rsp.append('%s DOC: %s' % (padded_name, item_dict['doc']))
        if tag == 'map':
          rsp.append('%s MAP: %s' % (dashes, str(item_dict['map_params'])))
        else:
          rsp.append('%s GET: %s' % (dashes, str(item_dict['get_params'])))
          rsp.append('%s SET: %s' % (dashes, str(item_dict['set_params'])))

    return '\n'.join(rsp)


def test():
  """Integration test.

  TODO(tbroch) Enhance integration test and add unittest (see mox)
  """
  # pylint: disable=protected-access,raising-format-tuple,g-doc-exception
  # Test method that's likely to be removed as more unit-tests roll out.
  logging.basicConfig(
      level=logging.DEBUG,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  scfg = SystemConfig()
  # TODO(tbroch) make this a comprenhensive test xml file
  scfg.add_cfg_file(os.path.join('data', 'servo.xml'))
  scfg.display_config()

  control_dict = scfg._lookup('control', 'goog_rec_mode')
  # checking mapping functionality
  control_params = control_dict['get_params']
  control_params = control_dict['set_params']
  if 'map' in control_params:
    map_name = control_params['map']
    map_dict = scfg._lookup('map', map_name)
    if not map_dict:
      raise Exception('Unable to find map %s', map_name)

    logging.info('')
    for keyname, val in map_dict['map_params'].iteritems():
      resolved_val = str(scfg.resolve_val(control_params, keyname))
      if resolved_val != val:
        logging.error('resolve failed for %s -> %s != %s', keyname, val,
                      resolved_val)

      # try re-mapping
      reformat_val = scfg.reformat_val(control_params, int(val))
      reformat_val = scfg.reformat_val(control_params, val)
      if reformat_val != keyname:
        logging.error('reformat failed for %s -> %s != %s', val, keyname,
                      reformat_val)


if __name__ == '__main__':
  test()
