# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
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
        ('ina219', 0x40, 'pp3300',          3.3, 0.01, 'loc', True),
        ('ina219', 0x41, 'pp3300_touch',    3.3, 0.01, 'loc', True),
        ('ina219', 0x42, 'pp3300_wifi',     3.3, 0.01, 'loc', True),
        ('ina219', 0x43, 'pp1800',          1.8, 0.01, 'loc', True),
        ('ina219', 0x44, 'pp1500_ap_io',    1.5, 0.01, 'loc', True),
        ('ina219', 0x45, 'pp1800_pmu',      1.8, 0.01, 'loc', True),
        ('ina219', 0x46, 'pp1800_pcie',     1.8, 0.01, 'loc', True),
        ('ina219', 0x47, 'pp1800_ap_avdd',  1.8, 0.01, 'loc', True),
        ('ina219', 0x48, 'pp3000',          3.0, 0.01, 'loc', True),
        ('ina219', 0x49, 'ppvar_bigcpu',    1.0, 0.01, 'loc', True),
        ('ina219', 0x4A, 'ppvar_gpu',       1.0, 0.01, 'loc', True),
        ('ina219', 0x4B, 'ppvar_litcpu',    1.0, 0.01, 'loc', True),
        ('ina219', 0x4C, 'ppvar_center',    0.9, 0.01, 'loc', True),
        ('ina219', 0x4D, 'pp1200_lpddr',    1.2, 0.01, 'loc', True),
        ('ina219', 0x4E, 'pp900_logic',     0.9, 0.01, 'loc', True),
        ('ina219', 0x4F, 'pp900_ap',        0.9, 0.01, 'loc', True),
       ]

