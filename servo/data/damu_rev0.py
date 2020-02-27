# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates damu_rev0
revs = [0]

inas = [
    ('ina3221', '0x40:0', 'ppvar_sys',          7.7, 0.020, 'rem', True), # R91200
    ('ina3221', '0x40:1', 'vbat',               7.7, 0.020, 'rem', True), # R90819
    ('ina3221', '0x40:2', 'pp1800_h1',          1.8, 0.050, 'rem', True), # R90364
    ('ina3221', '0x41:0', 'ppvar_bl',           7.7, 0.100, 'rem', True), # R391
    ('ina3221', '0x41:1', 'pp1800_ec',          1.8, 0.050, 'rem', True), # R90366
    ('ina3221', '0x41:2', 'pp3300_ctp',         3.3, 0.020, 'rem', True), # R90475
    ('ina3221', '0x42:0', 'pp3300_h1',          3.3, 0.050, 'rem', True), # R90365
    ('ina3221', '0x42:1', 'pp3300_wlan',        3.3, 0.020, 'rem', True), # R91136
    ('ina3221', '0x42:2', 'pp1800_wlan',        1.8, 0.020, 'rem', True), # R91139
    ('ina3221', '0x43:0', 'pp3300_lcm',         3.3, 0.020, 'rem', True), # R90518
    ('ina3221', '0x43:1', 'pp5000_dram',        5.0, 0.020, 'rem', True), # R90649
    ('ina3221', '0x43:2', 'pp5000_pmic',        5.0, 0.020, 'rem', True), # R90558
    ('ina219',  '0x44',   'pp3300_a',           3.3, 0.020, 'rem', True), # R90678
    ('ina219',  '0x45',   'ppvar_usb_c0_vbus', 20.0, 0.020, 'rem', True), # R90538
    ('ina219',  '0x46',   'pp1800_a',           1.8, 0.020, 'rem', True), # R90672
]
