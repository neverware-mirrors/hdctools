# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# for use with servo INA adapter board.  If measuring via servo V1 this can just
# be ignored.  clobber_ok added if user wishes to include servo_loc.xml
# additionally.
inline = """
  <map>
    <name>adc_mux</name>
    <doc>valid mux values for DUT's two banks of INA219 off PCA9540
    ADCs</doc>
    <params clobber_ok="" none="0" bank0="4" bank1="5"></params>
  </map>
  <control>
    <name>adc_mux</name>
    <doc>4 to 1 mux to steer remote i2c i2c_mux:rem to two sets of
    16 INA219 ADCs. Note they are only on leg0 and leg1</doc>
    <params clobber_ok="" interface="2" drv="pca9546" slv="0x70"
    map="adc_mux"></params>
  </control>
"""

inas = [
    ('ina219', 0x40, 'ppvar_vcc',       1.0, 0.002, 'loc0', True),  # L13
    ('ina219', 0x41, 'ppvat_gt',        1.0, 0.002, 'loc0', True),  # L31
    ('ina219', 0x42, 'ppvar_sa',        1.0, 0.005, 'loc0', True),  # L12
    ('ina219', 0x43, 'pp975_io',        7.7, 0.100, 'loc0', True),  # R111
    ('ina219', 0x44, 'pp5000_a',        5.0, 0.010, 'loc0', True),  # L24
    ('ina219', 0x45, 'pp3300_dsw',      3.3, 0.010, 'loc0', True),  # R513
    ('ina219', 0x46, 'pp3300_a',        7.7, 0.010, 'loc0', True),  # R144
    ('ina219', 0x47, 'pp1800_u_dram',   7.7, 0.100, 'loc0', True),  # R161
    ('ina219', 0x48, 'pp1200_vddq',     7.7, 0.100, 'loc0', True),  # R162
    ('ina219', 0x49, 'pp1000_a',        7.7, 0.100, 'loc0', True),  # R163
    ('ina219', 0x4a, 'pp850_prim_core', 7.7, 0.100, 'loc0', True),  # R164
    ('ina219', 0x4b, 'pp3300_dx_wlan',  3.3, 0.010, 'loc0', True),  # R645
    ('ina219', 0x4c, 'ppvar_bl_pwr',    7.7, 0.050, 'loc0', True),  # F1
    ('ina219', 0x4d, 'pp3300_dx_edp',   3.3, 0.010, 'loc0', True),  # R644
    ('ina219', 0x4e, 'pp3300_h1',       3.3, 0.100, 'loc0', True),  # R390
    ('ina219', 0x4f, 'vbat',            7.7, 0.020, 'loc0', True),  # R226
]
