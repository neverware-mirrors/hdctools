#!/usr/bin/python
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
# TODO(%s): for each ina control, fill in tuple as below.
# See other .py files for examples.
# DRV: what driver the inas use. It's usually 'ina3221' or 'ina219'.
# SLV: i2c slave addr
# CHAN: channel (in case of multi-channel INA (like 3221)
# NOM_VOLT: nominal voltage on the rail
# SENSE_RESISTOR: size of sense resistor attached - in Ohms.
# MUX:
# IS_CALIB: |True| if a sense resistor is available, and power & current
# readings can be configured. |False| otherwise.
inas = [
       #( DRV, SLV:CHAN, CTRL_NAME, NOM_VOLT, SENSE_RESISTOR, MUX, IS_CALIB),
        ('ina219',  0x40,  'pp3300_example',    3.3,     0.1, 'rem', True)
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
