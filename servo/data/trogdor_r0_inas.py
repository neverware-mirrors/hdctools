# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='servod'

revs = [ 0 ]

inline = """
  <map>
    <name>dut_adc_mux</name>
    <doc>valid mux values for DUT's two banks of INA3221 off PCA9540
    ADCs</doc>
    <params clobber_ok="" none="0" bank0="4" bank1="5"></params>
  </map>
  <control>
    <name>dut_adc_mux</name>
    <doc>2 to 1 mux to steer remote i2c dut_adc_mux:bank0/1 to two sets of
    12 INA3221 ADCs.</doc>
    <params clobber_ok="" interface="2" drv="pca9546" slv="0x70"
    map="dut_adc_mux"></params>
  </control>
"""

inas = [
        #('ina3221', '0x40:0', 'tp197/198',         0.00, 0.000,  'rem dut_adc_mux:bank0', True), # TP197/198
        #('ina3221', '0x40:1', 'tp199/200',         0.00, 0.000,  'rem dut_adc_mux:bank0', True), # TP199/TP200
        #('ina3221', '0x40:2', 'tp183/184',         0.00, 0.000,  'rem dut_adc_mux:bank0', True), # TP183/TP184
        ('ina3221', '0x41:0', 'pp600_l6a',          0.60, 0.010,  'rem dut_adc_mux:bank0', True), # R211
        ('ina3221', '0x41:1', 'pp1800_l10a',        1.80, 0.300,  'rem dut_adc_mux:bank0', True), # R209
        #('ina3221', '0x41:2', 'tp185/186',         0.00, 0.000,  'rem dut_adc_mux:bank0', True), # TP185/TP186
        ('ina3221', '0x42:0', 'pp1056_s4a',         1.056, 0.020, 'rem dut_adc_mux:bank0', True), # R201
        ('ina3221', '0x42:1', 'pp1000_l2a',         1.00, 0.050,  'rem dut_adc_mux:bank0', True), # R210
        ('ina3221', '0x42:2', 'pp1200_l1a',         1.20, 0.050,  'rem dut_adc_mux:bank0', True), # R208
        ('ina3221', '0x43:0', 'pp800_l8a',          0.80, 0.020,  'rem dut_adc_mux:bank0', True), # R204
        ('ina3221', '0x43:1', 'pp800_l9a',          0.80, 0.050,  'rem dut_adc_mux:bank0', True), # R205
        ('ina3221', '0x43:2', 'pp2850_l19a',        2.85, 0.050,  'rem dut_adc_mux:bank0', True), # R212
        #('ina3221', '0x40:0', 'tp203/204',         0.00, 0.000,  'rem dut_adc_mux:bank1', True), # TP203/204
        #('ina3221', '0x40:1', 'tp187/188',         0.00, 0.000,  'rem dut_adc_mux:bank1', True), # TP187/TP188
        ('ina3221', '0x40:2', 'pp1800_l1c',         1.80, 0.300,  'rem dut_adc_mux:bank1', True), # R215
        ('ina3221', '0x41:0', 'pp870_s5c_s6c',      0.87, 0.020,  'rem dut_adc_mux:bank1', True), # R193
        ('ina3221', '0x41:1', 'pp864_s7c',          0.864, 0.020, 'rem dut_adc_mux:bank1', True), # R194
        ('ina3221', '0x41:2', 'pp868_s1c_s2c_s3c',  0.868, 0.020, 'rem dut_adc_mux:bank1', True), # R196
        ('ina3221', '0x42:0', 'pp1300_l2c',         1.30, 0.050,  'rem dut_adc_mux:bank1', True), # R213
        ('ina3221', '0x42:1', 'pp3300_l10c',        3.30, 0.100,  'rem dut_adc_mux:bank1', True), # R216
        ('ina3221', '0x42:2', 'pp3300_l11c',        3.30, 0.100,  'rem dut_adc_mux:bank1', True), # R214
        # requires a rework, default resistor value on r0 is 0.002 Ohm
        ('ina3221', '0x43:0', 'src_vph_pwr',        4.00, 0.100,  'rem dut_adc_mux:bank1', True), # R321
        #('ina3221', '0x43:1', 'tp189/190',         0.00, 0.000,  'rem dut_adc_mux:bank1', True), # R205
        #('ina3221', '0x43:2', 'tp191/192',         0.00, 0.000,  'rem dut_adc_mux:bank1', True), # R212
]
