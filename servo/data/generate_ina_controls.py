#!/usr/bin/env python2
# Copyright 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper module to generate system control files for INA adcs."""

import argparse
import copy
import glob
import imp
import json
import os
import re
import sys
import time

from sweetberry_preprocessor import SweetberryPreprocessor
from servo_config_generator import ServoConfigFileGenerator
from servo_config_generator import ServoControlGenerator

class INAConfigGeneratorError(Exception):
  """Error class for INA control generation errors."""
  pass

class INAConfigGenerator(object):
  """Base class for any INA Configuration Generator.

  Shared base class that handles file name logic.

  Attributes:
    _configs_to_generate: a list of configurations that this template produces.
  """
  def __init__(self, module_name, ina_pkg):
    """Init all INA Configuration Generators.

    This sets up the common logic of deciding how many configurations to produce
    based on a given template.

    Args:
      module_name: name of template module
      ina_pkg: template loaded as a module
    """
    self._configs_to_generate = []
    if hasattr(ina_pkg, 'revs'):
      # modules need to be named board_[anything].py
      board = re.sub(r'_.*', '', module_name)
      for rev in ina_pkg.revs:
        try:
          self._configs_to_generate.append('%s_rev%d' % (board, int(rev)))
        except ValueError:
          raise INAConfigGeneratorError('Rev: %s has to be an integer.'
                                        % str(rev))
    else:
      # if rev doesn't exist, then it's an old-style INA file, in which case
      # this script produces just one control named the same as the module.
      self._configs_to_generate.append(module_name)

  def ExportConfig(self, outdir):
    """Export the configuration(s) of a template to outdir.

    This is required for each Generator class to implement.
    """
    raise NotImplementedError()


class PowerlogINAConfigGenerator(INAConfigGenerator):
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
    super(PowerlogINAConfigGenerator, self).__init__(module_name, ina_pkg)
    self._board_content, self._scenario_content = self.DumpADCs(ina_pkg.inas)

  def DumpADCs(self, adcs):
    """Dump json formatted INA231 configurations for powerlog configuration.

    This uses the same adcs template formate as servod (for compatability)
    but sweetberry configuration only needs slv, name, sense, and is_calib.

    Args:
      adcs: array of adc elements.  Each array element is a tuple consisting of:
          drvname: string name of adc driver to enumerate to control the adc
          slv: string formatted '0xAA:B': AA is i2c slv addr and B is i2c port
          name: string name of the power rail
          nom: float of nominal voltage of power rail
          sense: float of sense resitor size in ohms
          mux: string name of bank on sweetberry these ADC's live on: j2, j3, j4
          is_calib: boolean to indicate if calibration is possible for this rail
                    if false, no config will be exported

    The adcs list above is in order, meaning this function looks for name at
    adc[2], where adc is the tuple for a particular adc.

    Returns:
      Tuple of (board_content, scenario_content):
        board_content: json list of dictionaries describing INAs used
        scenario_content: json list of INA names in board_content
    """
    adc_list = []
    rails = []
    for (drvname, slv, name, nom, sense, mux, is_calib) in adcs:
      if is_calib:
        addr, port = [int(entry, 0) for entry in slv.split(':')]
        adc_list.append('  %s' % json.dumps({'name': name,
                                             'rs': float(sense),
                                             'sweetberry': 'A',
                                             'addr': addr,
                                             'port': port}))
      rails.append(name)
    adc_lines = ',\n'.join(adc_list)
    return ('[\n%s\n]' % adc_lines,
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
    _outfile_gen = servo config xml generator.
  """

  def __init__(self, module_name, ina_pkg, servo_data_dir, servo_drv_dir=None):
    """Setup Generator by preparing an xml generator to output entire config.

    Args:
      module_name: name of the template module
      ina_pkg: template loaded as a module
      servo_data_dir: servo data directory to include configs
      servo_drv_dir: servo drv directory to check drv availability
    """
    super(ServoINAConfigGenerator, self).__init__(module_name, ina_pkg)
    if not servo_drv_dir:
      servo_drv_dir = os.path.join(servo_data_dir, '..', 'drv')
    self._servo_drv_dir = servo_drv_dir
    ina2xx_drv_cfg = os.path.join(servo_data_dir, 'ina2xx.xml')
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

    if os.path.isfile(ina2xx_drv_cfg):
      includes.append(os.path.basename(ina2xx_drv_cfg))
    if hasattr(ina_pkg, 'inline'):
      inline = ina_pkg.inline
    else:
      inline = ''


    ctrl_gens = self.DumpADCs(ina_pkg.inas, interface)
    self._outfile_gen = ServoConfigFileGenerator(ctrl_generators=ctrl_gens,
                                                 includes=includes,
                                                 inline=inline,
                                                 intro_comments=comments)

  def DumpADCs(self, adcs, interface=2):
    """Dump XML formatted INAxxx adcs for servod.

    Args:
      adcs: array of adc elements.  Each array element is a tuple consisting of:
          drvname: string name of adc driver to enumerate to control the adc.
          slv: int representing the i2c slave address.
               optional channel/port if ADC (INA3221 only) has multiple channels
               or adc is on a different i2c port (sweetberry only). For example,
                 "0x40"   : address 0x40 ... no channel/port
                 "0x40:1" : address 0x40, channel/port 1
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
    control_generators = []
    for (drvname, slv, name, nom, sense, mux, is_calib) in adcs:
      drvpath = os.path.join(self._servo_drv_dir, drvname + '.py')
      if not os.path.isfile(drvpath):
        raise INAConfigGeneratorError('Unable to locate driver for %s at %s'
                                      % (drvname, drvpath))
      ina_type = 'ina231' if drvname == 'sweetberry' else drvname
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

      if ina_type == 'ina231':
        regs.extend(['msken', 'alrt'])
      elif ina_type == 'ina3221':
        regs = ['cfg', 'shv', 'busv', 'msken']

      if ina_type == 'ina3221':
        (slv, chan_id) = slv.split(':')
        params_base['slv'] = slv
        params_base['channel'] = chan_id

      if drvname == 'sweetberry':
        (slv, port) = slv.split(':')
        params_base['slv'] = slv
        params_base['port'] = port

      mv_ctrl_docstring = ('Bus Voltage of %s rail in millivolts on i2c_mux:%s'
                           % (name, params_base['mux']))
      mv_ctrl_params = {'subtype' : 'millivolts',
                        'nom'     : nom}
      mv_ctrl_params.update(params_base)
      control_generators.append(ServoControlGenerator(name + '_mv',
                                                     mv_ctrl_docstring,
                                                     mv_ctrl_params))

      shuntmv_ctrl_docstring = ('Shunt Voltage of %s rail in millivolts '
                                'on i2c_mux:%s' % (name, params_base['mux']))
      shuntmv_ctrl_params = {'subtype'  : 'shuntmv',
                             'nom'      : nom}
      shuntmv_ctrl_params.update(params_base)
      control_generators.append(ServoControlGenerator(name + '_shuntmv',
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
        control_generators.append(ServoControlGenerator(name + '_ma',
                                                       ma_ctrl_docstring,
                                                       ma_ctrl_params))

        mw_ctrl_docstring = ('Power of %s rail in milliwatts '
                             'on i2c_mux:%s' % (name, params_base['mux']))
        mw_ctrl_params = {'subtype' : 'milliwatts'}
        mw_ctrl_params.update(params_base)
        control_generators.append(ServoControlGenerator(name + '_mw',
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
          if reg == 'cfg':
            reg_ctrl_params_set['map'] = '%s_cfg' % ina_type
        control_generators.append(ServoControlGenerator(reg_ctrl_name,
                                                       reg_ctrl_docstring,
                                                       reg_ctrl_params_get,
                                                       reg_ctrl_params_set))
    return control_generators

  def ExportConfig(self, outdir):
    """Write the configuration files in the outdir.

    Dump the XML Servo Configuration(s) for this generator.

    Args:
      outdir: Directory to place the configuration files into.
    """
    for outfile in self._configs_to_generate:
      outfile_dest = os.path.join(outdir, '%s.xml' % outfile)
      self._outfile_gen.WriteToFile(outfile_dest)

def GenerateINAControls(servo_data_dir, servo_drv_dir=None, outdir=None,
                        export=True, candidates=[]):
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
    export: if True config files will be exported to |outdir|
            if False it's only a dry-run to detect errors
    candidates: list of files in |servo_data_dir| to generate configs for.
                if empty, all files in |servo_data_dir| will be considered.
  """
  if not outdir:
    outdir = servo_data_dir
  generators = []
  if not candidates:
    candidates = os.listdir(servo_data_dir)
  for candidate in candidates:
    if candidate.endswith('.py'):
      module_name = candidate[:-3]
      ina_pkg = imp.load_module(module_name,
                                *imp.find_module(module_name,
                                                 [servo_data_dir]))
      if not hasattr(ina_pkg, 'inas'):
        continue
      if hasattr(ina_pkg, 'config_type'):
        config_type = ina_pkg.config_type
      else:
      # If config_type is not defined, it is a servod config
        config_type = 'servod'
      if config_type not in ['sweetberry', 'servod']:
        raise INAConfigGeneratorError('Unknown config type %s' % config_type)
      if config_type == 'sweetberry':
        #translate inas from pin-style to i2c-addr style config (if applicable)
        ina_pkg.inas = SweetberryPreprocessor.Preprocess(ina_pkg.inas)
        #also output powerlog config files (.board/.scenario)
        generators.append(PowerlogINAConfigGenerator(module_name,
                                                     ina_pkg))
      #always output Servod configurations
      generators.append(ServoINAConfigGenerator(module_name,
                                                ina_pkg,
                                                servo_data_dir,
                                                servo_drv_dir))
  if export:
    for generator in generators:
      generator.ExportConfig(outdir)

def main(cmdline=sys.argv[1:]):
  """cmdline interface to generate &| verify config files.

  Note: This is mainly inteded as a development tool to verify a new or
  modified powermap before submitting it, and without having to build the full
  hdctools.
  """
  parser = argparse.ArgumentParser(description='cmdline tool to generate and '
                                   'validate servod power configurations.')
  parser.add_argument('--dry-run', default=False, action='store_true',
                      help='Do not export files, only verify that no errors '
                      'on config generation occur.')
  parser.add_argument('-i', '--input', action='store',
                      default=os.path.dirname(__file__),
                      help='file or directory to perform conversions on.')
  args = parser.parse_args(cmdline)
  if os.path.isdir(args.input):
    servo_data_dir = args.input
    candidates = glob.glob(os.path.join(servo_data_dir, '*.py'))
  if os.path.isfile(args.input):
    servo_data_dir = os.path.dirname(args.input)
    candidates = [args.input]
  #having only the basename is required for load_module to work better
  candidates = [os.path.basename(candidate) for candidate in candidates]
  #if dry_run is set then we don't want to export.
  export = not args.dry_run
  for candidate in candidates:
    try:
      GenerateINAControls(servo_data_dir=servo_data_dir,
                          export=export,
                          candidates=[candidate])
      msg_prefix = 'Success:'
    except Exception as e:
      msg_prefix = 'FAILURE: %s' % e.message
    print('%s for candidate file %s' % (msg_prefix, candidate))

if __name__ == '__main__':
  main()
