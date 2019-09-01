#!/usr/bin/python2
# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import argparse
import datetime
import getpass
import sys

default_outfile = 'new_ina_map'

year = datetime.datetime.now().year
user = getpass.getuser()

copyright_string = """\
# Copyright %d The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
""" % year

config_tag_str = """
# TODO(%s): fill in to generate servod or sweetberry configuration.
config_type  = 'sweetberry' | 'servod'
""" % user

rev_tag_str = """
# TODO(%s): fill in which revisions use this INA map.
revs  = [ 'REV_ID(int)']
""" % user

ina_tag_str = """
# TODO(%s): for each ina control fill in tuple as example below. Examples
# include all types of supported tuples, depending on your needs.
# See other .py files for examples.
# DRV: what driver the inas use. 'ina219' 'ina231' 'ina3221' 'sweetberry'.
# SLV: i2c slave addr. For sweetberry this can also be a medusa header pin
#      tuple, e.g. (1,3).
# SUFFIX: in combination with 'ina3221': channel of the INA rail is on.
#                             'sweetberry': i2c port the INA is on.
# NOM_VOLT: nominal voltage on the rail.
# SENSE_RESISTOR: size of sense resistor attached - in Ohms.
# MUX: i2c location to generate docstring. Note: if the SLV above is written
#      as a tuple, then this must be 'j2', 'j3', or 'j4' (sweetberry banks).
# IS_CALIB: |True| if a sense resistor is available, and power & current
#           readings can be configured. |False| otherwise.
inas = [
       #( DRV,         SLV:SUFFIX,  CTRL_NAME,        NOM-V, R,    MUX, CALIB),
        ('ina219',     '0x40',      'ppvar_219',      3.3,   0.1,  'rem', True),
        ('ina231',     '0x40',      'ppvar_231',      3.3,   0.1,  'rem', True),
        ('ina3221',    '0x40:2',    'ppvar_3221',     3.3,   0.1,  'rem', True),
        ('sweetberry', (1,3),       'ppvar_sb_pins',  3.3,   0.1,  'j2',  True),
        ('sweetberry', '0x40:3',    'ppvar_sb_addr',  3.3,   0.1,  'j2',  True),
]
""" % user

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Measure power using servod.')
  parser.add_argument('-n', '--name', default='')
  args = parser.parse_args(sys.argv[1:])
  outfile = args.name
  if not len(outfile):
    outfile = default_outfile
  outfile += '.py'
  with open(outfile, 'w') as f:
    f.write(copyright_string)
    f.write('\n')
    f.write(config_tag_str)
    f.write('\n')
    f.write(rev_tag_str)
    f.write('\n')
    f.write(ina_tag_str)
    f.write('\n')
  print("Finished creating ina skeleton file at:\n%s" % outfile)
