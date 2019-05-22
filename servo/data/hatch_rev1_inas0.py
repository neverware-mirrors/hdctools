# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='servod'

inas = [('ina3221', '0x40:0', 'pp3300_g',             3.30, 0.100, 'rem', True), # PR17,Global power rail, original 0.005ohm
        ('ina3221', '0x40:1', 'pp3300_a_wlan',        3.30, 0.020, 'rem', True), # R409
        ('ina3221', '0x40:2', 'pp2500_dram',          2.50, 0.200, 'rem', True), # PRM9,Memory power rail
        ('ina3221', '0x41:0', 'pp950_vccio',          0.95, 0.005, 'rem', True), # PR89,IO power rail
        ('ina3221', '0x41:1', 'ppvar_a_vccprim_core', 7.60, 0.010, 'rem', True), # PR72,PCH Core rail (Primary Well), original 0.002ohm
        ('ina3221', '0x41:2', 'pp1800_a',             1.80, 0.010, 'rem', True), # PR38,Primary rail
        ('ina3221', '0x42:0', 'pp3300_a',             3.30, 0.020, 'rem', True), # R203,Primary rail
        ('ina3221', '0x42:1', 'pp5000_a',             5.00, 0.010, 'rem', True), # PR506,Primary rail, original 0.002ohm
        ('ina3221', '0x42:2', 'pp3300_a_soc',         3.30, 0.100, 'rem', True), # R410
        ('ina3221', '0x43:0', 'pp3300_dx_edp',        3.30, 0.020, 'rem', True), # R417,Panel power rail
        ('ina3221', '0x43:1', 'pp3300_ec',            3.30, 0.500, 'rem', True), # R415
        ('ina3221', '0x43:2', 'pp1050_a',             1.05, 0.010, 'rem', True), # PR57,Primary rail, original 0.002ohm
        ('ina219',  '0x4a',   'pp1200_vddq',          1.20, 0.002, 'rem', True)] # PRM14,Processor and Memory power rail
