#!/usr/bin/env python2
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Based on suggestions in http://guide.python-distribute.org/creation.html
# ...with a mix of bits from pymox.

import imp
import os
from setuptools import setup
from setuptools.command import build_py
import sys

class servo_build_py(build_py.build_py):
  """ Custom build_py class for servod to do setup """

  # The only reason we include the servo.data package is to build INA
  # XML configuration files from simplified .py files. So we pop it
  # out to avoid building the python files.
  # See generate_ina_controls.py & servo/data/README.md for more
  # information.
  def run(self):
    """ Generate .xml servod configuration files from the servo/data/*.py
        files before removing the servo.data package.
    """
    data_dir = self.get_package_dir(self.packages.pop(1))
    sys.path.append(data_dir)
    module_name = 'generate_ina_controls'
    ina_generator = imp.load_module(module_name, *imp.find_module(module_name,
                                                                  [data_dir]))
    ina_generator.GenerateINAControls(data_dir)
    build_py.build_py.run(self)

execfile('version.py')

#overwrite setup tools here to do the following:

# get package_data files
# run generate_ina_controls.py over all the files,
# giving the file an output directory?

setup(
  name = "servo",
  version = __version__,
  package_dir = {'' : 'build'},
  py_modules=['servo.servod', 'servo.dut_control'],
  packages=['servo', 'servo.data', 'servo.drv'],
  package_data={'servo': ['data/*.xml',
                          'data/*.scenario',
                          'data/*.board']},
  cmdclass={'build_py': servo_build_py},
  url = "http://www.chromium.org",
  maintainer='chromium os',
  maintainer_email='chromium-os-dev@chromium.org',
  license = "Chromium",
  description = "Server to communicate and control servo debug board.",
  long_description = "Server to communicate and control servo debug board.",
  entry_points={
    'console_scripts': [
      'servod = servo.servod:main',
      'dut-control = servo.dut_control:main',
      'dut-power = servo.dut_power:main',
      'servodutil = servo.servodutil:main'
    ]
  }
)

setup(
  name = "usbkm232",
  version = __version__,
  package_dir = {'' : 'build'},
  py_modules=['usbkm232.ctrld', 'usbkm232.ctrlu', 'usbkm232.enter',
              'usbkm232.space', 'usbkm232.tab'],
  packages=['usbkm232'],
  url = "http://www.chromium.org",
  maintainer='chromium os',
  maintainer_email='chromium-os-dev@chromium.org',
  license = "Chromium",
  description = "Communicate and control usbkm232 USB keyboard device.",
  long_description = "Communicate and control usbkm232 USB keyboard device.",
  entry_points={
    'console_scripts': [
      'usbkm232-ctrld = usbkm232.ctrld:main',
      'usbkm232-ctrlu = usbkm232.ctrlu:main',
      'usbkm232-enter = usbkm232.enter:main',
      'usbkm232-space = usbkm232.space:main',
      'usbkm232-tab = usbkm232.tab:main',
      'usbkm232-test = usbkm232.usbkm232:main',
    ]
  }
)

setup(
  name = "servo_mfg",
  version = __version__,
  package_dir = {'' : 'servo/scripts'},
  py_modules=['servo_mfg' ],
  packages=['servo_mfg'],
  package_data={'servo_mfg': ['binfiles/*.hex',
                              '*.sh']},
  url = "http://www.chromium.org",
  maintainer='chromium os',
  maintainer_email='chromium-os-dev@chromium.org',
  license = "Chromium",
  description = "Tools to program and validate servo devices.",
  entry_points={
    'console_scripts': [
        'mfg_servo_v4 = servo_mfg.mfg_servo_v4:main',
        'mfg_servo_micro = servo_mfg.mfg_servo_micro:main',
    ]
  }
)
