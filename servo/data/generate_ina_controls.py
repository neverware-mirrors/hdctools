# Copyright 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper module to generate system control files for INA219 adcs."""
import copy
import imp
import json
import os
import re
import time


class XMLElementGenerator(object):
  """Helper class to generate a formatted XML element.

  Attributes:
    _name: name of the element
    _text: text to go between opening and close brackets
    _attribute_string: string containing attributes and values for element
  """


  def __init__(self, name, text, attributes={}, attribute_order=[]):
    """Prepare substrings to make formatted XML element retrieval easier.

    Args:
      name: name of the element <[name]>.
      text: text to go between opening and closing tag.
      attributes: key/value pairs of attributes for the tag.
      attribute_order: order in which to print the attributes.
    """
    self._name = name
    self._text = text
    keys = [k for k in attribute_order if k in attributes]
    keys += list(set(attributes.keys()) - set(attribute_order))
    self._attribute_string = ''.join(' %s="%s"' %
                                     (k, attributes[k]) for k in keys)

  def GetXML(self, newline_for_text=False):
    """Retrieves XML string for element.

    Args:
      newline_for_text: if |True|, introduce a newline after opening
                        tag and before closing tag.

    Returns:
      formatted string for the element.
    """
    output_format = '<%s%s>\n%s\n</%s>'
    if not newline_for_text:
      output_format.replace('\n', '')
    return output_format % (self._name, self._attribute_string,
                            self._text, self._name)


class ServoControlGenerator(object):
  """Helper class to generate formatted XML for servo controls.

  Attributes:
    _ctrl_elements: list XMLElementGenerators to build control
                    element on retrieval.
  """

  # order of the attributes for the params element.
  params_attr_order = ['cmd', 'interface', 'drv', 'slv',
                       'channel', 'type', 'subtype']

  def __init__(self, name, docstring, params, params2=None):
    """Init an XMLElementGenerator for each element.

    Prepare control XML retrieval by preparing XML generators for each
    component.

    Args:
      name: name tag for the control
      docstring: docstring for the control
      params: attributes for the params tag
      params2: attributes for the 2nd params tag
               (applicable for controls that have both set & get)

    Raises:
      INAConfigGeneratorError if two malformatted params elements are
      provided.
    """
    parameters = [params]
    if params2:
      # checking to make sure that if there are two paramteter sets, one of them
      # is a set command and the other is a get command.
      if 'cmd' not in params or 'cmd' not in params2:
        raise INAConfigGeneratorError('Control %s has 2 params. cmd attribute '
                                      'is required for each param.' % name)
      cmds = set([params['cmd'], params2['cmd']])
      if cmds != set(['get', 'set']):
        raise INAConfigGeneratorError("Control %s has 2 params, and cmd "
                                      "attributes are not 'set' and 'get'"
                                      % name)
      parameters.append(params2)

    self._ctrl_elements = [XMLElementGenerator('name', name),
                           XMLElementGenerator('doc', docstring)]
    for parameter in parameters:
      self._ctrl_elements.append(XMLElementGenerator('params', '',
                                                     parameter,
                                                     self.params_attr_order))

  def GetControlXML(self):
    """Retrieves XML string for a servod control.

    Returns:
      formatted string for the XML control.
    """
    # for each control element, generate the XML and join together into one
    # string.
    ctrl_text = '\n'.join(element.GetXML() for element in self._ctrl_elements)
    ctrl_element = XMLElementGenerator('control', ctrl_text, {})
    return ctrl_element.GetXML()


class XMLFileGenerator(object):
  """Helper to generate XML servod configuration files.

  Attributes:
    _text: xml file as a string
  """

  XML_VERSION = '1.0'

  def __init__(self, body, includes=None, intro_comments=''):
    """Prepares entire XML file as a string for easier export later.

    Args:
      body: xml file body as a string
      includes: list of xml files to include
      intro_comments: comments to add in the beginning.
    """
    self._text = '<?xml version="%s"?>\n' % self.XML_VERSION
    true_body = ''
    if intro_comments:
      true_body += '<!-- %s -->\n' % intro_comments
    if includes:
      for include in includes:
        name_element = XMLElementGenerator(name='name', text=include)
        include_tag = XMLElementGenerator(name='include',
                                          text=name_element.GetXML())
        true_body += '%s\n' % include_tag.GetXML()
    true_body += body
    file_as_element = XMLElementGenerator(name='root', text=true_body)
    self._text += file_as_element.GetXML(newline_for_text=True)

  def WriteToFile(self, destination, run_tidy=True):
    """Helper to write to file. Runs tidy after file is written.

    Args:
      destination: dest where to save the file.
      run_tidy: runs tidy if |True|
    """
    with open(destination, 'w') as f:
      f.write(self._text)

    if run_tidy:
      rv = os.system('tidy -quiet -mi -xml %s' % destination)
      if rv:
        raise INAConfigGeneratorError('Running tidy on %s failed.'
                                      % destination)

  def GetAsString(self):
    """Get entire XML configuration file as a string.

    Returns:
      formatted string for the entire XML config file.
    """
    return self._text


class INAConfigGeneratorError(Exception):
  """Error class for INA control generation errors."""
  pass


class INAConfigGenerator(object):
  """Base class for any INA Configuration Generator.

  Shared base class that handles file name logic.

  Attributes:
    _configs_to_generate: a list of configurations that this template produces.
  """
  def __init__(self, ina_pkg, module_name):
    """Init all INA Configuration Generators.

    This sets up the common logic of deciding how many configurations to produce
    based on a given template.

    Args:
      ina_pkg: template loaded as a module
      module_name: name of template module
    """
    self._configs_to_generate = []
    try:
      # modules need to be named board_[anything].py
      board = re.sub(r'_.*', '', module_name)
      for rev in ina_pkg.revs:
        self._configs_to_generate.append('%s_rev_%d' % (board, int(rev)))
    except AttributeError:
      # if controls_to_generate doesn't exist, then it's an old-style
      # INA file, in which case this script produces just one control,
      # named the same as the module.
      self._configs_to_generate.append(module_name)
    except ValueError:
      raise INAConfigGeneratorError('Rev: %s has to be an integer.'
                                    % str(rev))

  def ExportConfig(self, outdir):
    """Export the configuration(s) of a template to outdir.

    This is required for each Generator class to implement.
    """
    raise NotImplementedError()


class SweetberryINAConfigGenerator(INAConfigGenerator):
  """Generator to make sweetberry configurations given a template.

  Attributes:
    _board_content = content of string for .board Sweetberry file.
    _scenario_content = content of string for .scenario Sweetberry file.
  """

  def __init__(self, module_name, ina_pkg):
    """Setup Generator by generating file contents as string.

    Args:
      module_name: name of the template module
      ina_pkg: template loaded as a module
    """
    super(SweetberryINAConfigGenerator, self).__init__(ina_pkg, module_name)
    self._board_content, self._scenario_content = self.DumpADCs(ina_pkg.inas)

  def DumpADCs(self, adcs):
    """Dump json formatted INA231 configurations for Sweetberry board.

    While this uses the same adcs template formate as servod (for compatability,
    Sweetberry configuration only needs slv, name, and sense.

    Args:
      adcs: array of adc elements.  Each array element is a tuple consisting of:
          drvname: string name of adc driver to enumerate to control the adc.
          slv: int representing the i2c slave address
          name: string name of the power rail
          nom: float of nominal voltage of power rail.
          sense: float of sense resitor size in ohms
          mux: string name of i2c mux leg these ADC's live on
          is_calib: boolean to indicate if calibration is possible for this rail
      interface: interface index to handle low-level communication.

    The adcs list above is in order, meaning this function looks for name at
    adc[2], where adc is the tuple for a particular adc.

    Returns:
      Tuple of (board_content, scenario_content):
        board_content: json list of dictionaries describing INAs used
        scenario_content: json list of INA names in board_content
    """
    adc_lines = ''
    rails = []
    for (drvname, slv, name, nom, sense, mux, is_calib) in adcs:
      adc_lines = '%s%s\n' % (adc_lines,
                              json.dumps({'name': name,
                                          'rs': float(sense),
                                          'sweetberry': 'A',
                                          'channel': slv - 64}))
      rails.append(name)
    return ('[\n%s]' % adc_lines,
            json.dumps(rails, indent=2))

  def ExportConfig(self, outdir):
    """Write the configuration files in the outdir.

    Dump the Sweetberry Configuration(s) for this generator.

    Args:
      outdir: Directory to place the configuration files into.
    """
    for outfile in self._configs_to_generate:
      board_outpath = os.path.join(outdir, '%s.board' % outfile)
      scenario_outpath = os.path.join(outdir, '%s.scenario' % outfile)
      with open(scenario_outpath, 'w') as f:
        f.write(self._scenario_content)
      with open(board_outpath, 'w') as f:
        f.write(self._board_content)


class ServoINAConfigGenerator(INAConfigGenerator):
  """Generator to make servod configurations given a template.

  Attributes:
    _servo_drv_dir = servo directory to check for ina driver.
    _outfile_generator = servo config xml generator.
  """

  def __init__(self, module_name, ina_pkg, servo_data_dir, servo_drv_dir=None):
    """Setup Generator by preparing an xml generator to output entire config.

    Args:
      module_name: name of the template module
      ina_pkg: template loaded as a module
      servo_data_dir: servo data directory to include configs
      servo_drv_dir: servo drv directory to check drv availability
    """
    super(ServoINAConfigGenerator, self).__init__(ina_pkg, module_name)
    if not servo_drv_dir:
      servo_drv_dir = os.path.join(servo_data_dir, '..', 'drv')
    self._servo_drv_dir = servo_drv_dir
    ina2xx_drv_cfg = os.path.join(servo_data_dir, 'ina2xx.xml')
    powertools_drv_cfg = os.path.join(servo_data_dir, 'power_tools.xml')
    if hasattr(ina_pkg, 'interface'):
      interface = ina_pkg.interface
      if type(interface) != int:
        raise INAConfigGeneratorError('Invalid interface %r, should be int.'
                                      % interface)
    else:
      interface = 2  # default I2C interface

    comments = 'Autogenerated on %s' % time.asctime()
    includes = []
    body = ''

    if os.path.isfile(powertools_drv_cfg):
      includes.append(os.path.basename(powertools_drv_cfg))
    if os.path.isfile(ina2xx_drv_cfg):
      includes.append(os.path.basename(ina2xx_drv_cfg))
    if hasattr(ina_pkg, 'inline'):
      body += '%s\n' % ina_pkg.inline

    body += self.DumpADCs(ina_pkg.inas, interface)
    self._outfile_generator = XMLFileGenerator(body=body, includes=includes,
                                               intro_comments=comments)

  def DumpADCs(self, adcs, interface=2):
    """Dump XML formatted INAxxx adcs for servod.

    Args:
      adcs: array of adc elements.  Each array element is a tuple consisting of:
          drvname: string name of adc driver to enumerate to control the adc.
          slv: int representing the i2c slave address plus optional channel if
               ADC (INA3221 only) has multiple channels.  For example,
                 "0x40"   : address 0x40 ... no channel
                 "0x40:1" : address 0x40, channel 1
          name: string name of the power rail
          nom: float of nominal voltage of power rail.
          sense: float of sense resitor size in ohms
          mux: string name of i2c mux leg these ADC's live on
          is_calib: boolean to indicate if calibration is possible for this rail
      interface: interface index to handle low-level communication.

    The adcs list above is in order, meaning this function looks for name at
    adc[2], where adc is the tuple for a particular adc.

    Returns:
      string (large) of XML for the system config of these ADCs to eventually be
      parsed by servod daemon ( servo/system_config.py )
    """
    all_controls = ''
    for (drvname, slv, name, nom, sense, mux, is_calib) in adcs:
      drvpath = os.path.join(self._servo_drv_dir, drvname + '.py')
      if not os.path.isfile(drvpath):
        raise INAConfigGeneratorError('Unable to locate driver for %s at %s'
                                      % (drvname, drvpath))
      controls_for_rail = []
      params_base = {
          'type'      : 'get',
          'drv'       : drvname,
          'interface' : interface,
          'slv'       : slv,
          'mux'       : mux,
          'rsense'    : sense,
      }
      # Must match REG_IDX.keys() in servo/drv/ina2xx.py
      regs = ['cfg', 'shv', 'busv', 'pwr', 'cur', 'cal']

      if drvname == 'ina231':
        regs.extend(['msken', 'alrt'])
      elif drvname == 'ina3221':
        regs = ['cfg', 'shv', 'busv', 'msken']

      if drvname == 'ina3221':
        (slv, chan_id) = slv.split(':')
        params_base['slv'] = slv
        params_base['channel'] = chan_id

      mv_ctrl_docstring = ('Bus Voltage of %s rail in millivolts on i2c_mux:%s'
                           % (name, params_base['mux']))
      mv_ctrl_params = {'subtype' : 'millivolts',
                        'nom'     : nom}
      mv_ctrl_params.update(params_base)
      controls_for_rail.append(ServoControlGenerator(name + '_mv',
                                                     mv_ctrl_docstring,
                                                     mv_ctrl_params))

      shuntmv_ctrl_docstring = ('Shunt Voltage of %s rail in millivolts '
                                'on i2c_mux:%s' % (name, params_base['mux']))
      shuntmv_ctrl_params = {'subtype'  : 'shuntmv',
                             'nom'      : nom}
      shuntmv_ctrl_params.update(params_base)
      controls_for_rail.append(ServoControlGenerator(name + '_shuntmv',
                                                     shuntmv_ctrl_docstring,
                                                     shuntmv_ctrl_params))

      # in some instances we may not know sense resistor size ( re-work ) or
      # other custom factors may not allow for calibration and those reliable
      # readings on the current and power registers.  This boolean determines
      # which controls should be enumerated based on rails input specification
      if is_calib:
        ma_ctrl_docstring = ('Current of %s rail in milliamps '
                             'on i2c_mux:%s' % (name, params_base['mux']))
        ma_ctrl_params = {'subtype' : 'milliamps'}
        ma_ctrl_params.update(params_base)
        controls_for_rail.append(ServoControlGenerator(name + '_ma',
                                                       ma_ctrl_docstring,
                                                       ma_ctrl_params))

        mw_ctrl_docstring = ('Power of %s rail in milliwatts '
                             'on i2c_mux:%s' % (name, params_base['mux']))
        mw_ctrl_params = {'subtype' : 'milliwatts'}
        mw_ctrl_params.update(params_base)
        controls_for_rail.append(ServoControlGenerator(name + '_mw',
                                                       mw_ctrl_docstring,
                                                       mw_ctrl_params))
      for reg in regs:
        reg_ctrl_docstring = ('Raw register value of %s on i2c_mux:%s'
                              % (reg, params_base['mux']))
        reg_ctrl_name = '%s_%s_reg' % (name, reg)
        reg_ctrl_params_get = {'cmd'      : 'get',
                               'subtype'  : 'readreg',
                               'fmt'      : 'hex',
                               'reg'      : reg}
        reg_ctrl_params_get.update(params_base)
        # rsense and type are in params_base, but not needed here
        del reg_ctrl_params_get['rsense']
        del reg_ctrl_params_get['type']
        reg_ctrl_params_set = None
        if reg in ['cfg', 'cal']:
          reg_ctrl_params_set = copy.copy(reg_ctrl_params_get)
          reg_ctrl_params_set.update({'cmd'      : 'set',
                                      'subtype'  : 'writereg'})
          if reg == 'cal':
            reg_ctrl_params_set['map'] = 'calibrate'
        controls_for_rail.append(ServoControlGenerator(reg_ctrl_name,
                                                       reg_ctrl_docstring,
                                                       reg_ctrl_params_get,
                                                       reg_ctrl_params_set))
      for generator in controls_for_rail:
        all_controls += generator.GetControlXML()

    return all_controls

  def ExportConfig(self, outdir):
    """Write the configuration files in the outdir.

    Dump the XML Servo Configuration(s) for this generator.

    Args:
      outdir: Directory to place the configuration files into.
    """
    for outfile in self._configs_to_generate:
      outfile_dest = os.path.join(outdir, '%s.xml' % outfile)
      self._outfile_generator.WriteToFile(outfile_dest)

def GenerateINAControls(servo_data_dir, servo_drv_dir=None, outdir=None):
  """Attempt to generate INA configurations for all modules.

  Generates the configuration for every module found inside
  |self._servo_data_dir| during init.

  Optionally also provide where to write configurations to, and where to
  look for servo drv files if not at known location.

  Args:
    servo_data_dir: directory where to look for .py files to generate
                    controls.
    servo_drv_dir: directory where servo drivers are. Used to verify
                   that defined controls have a driver they can use.
                   If |None|, generator will look for drivers at
                   servo_data_dir/../drv/
    outdir: directory where to dump generated configuration files.
            If |None|, config files are dumped into |servo_data_dir|
  """
  if not outdir:
    outdir = servo_data_dir
  generators = []
  for candidate in os.listdir(servo_data_dir):
    if candidate.endswith('.py'):
      module_name = candidate[:-3]
      ina_pkg = imp.load_module(module_name,
                                *imp.find_module(module_name,
                                                 [servo_data_dir]))
      if not hasattr(ina_pkg, 'inas'):
        continue
      try:
        config_type = ina_pkg.config_type
      except AttributeError:
      # If config_type is not defined, it is a servod config
        config_type = 'servod'
      if config_type not in ['sweetberry', 'servod']:
        raise INAConfigGeneratorError('Unknown config type %s' % config_type)
      if config_type == 'sweetberry':
        generators.append(SweetberryINAConfigGenerator(module_name,
                                                       ina_pkg))
      else:
        generators.append(ServoINAConfigGenerator(module_name,
                                                  ina_pkg,
                                                  servo_data_dir,
                                                  servo_drv_dir))
  for generator in generators:
    generator.ExportConfig(outdir)
