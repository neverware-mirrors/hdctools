# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates asurada_rev0
revs = [0]

inas = [
    ('ina3221', '0x40:0', 'ppvar_vbus_in', 20.0, 0.020, 'rem', True), # R277
    ('ina3221', '0x40:1', 'ppvar_batt',     8.8, 0.010, 'rem', True), # R665
    ('ina3221', '0x40:2', 'pp4200_g',       4.2, 0.010, 'rem', True), # RS16
    ('ina3221', '0x41:0', 'ppvar_bl',       8.8, 0.010, 'rem', True), # R276
    ('ina3221', '0x41:1', 'pp3300_g',       3.3, 0.020, 'rem', True), # RS6
    ('ina3221', '0x41:2', 'pp5000_a',       5.0, 0.010, 'rem', True), # RS7
    ('ina3221', '0x42:0', 'pp3300_h1_g',    3.3, 0.020, 'rem', True), # RS12
    ('ina3221', '0x42:1', 'ppvar_sys',      8.8, 0.010, 'rem', True), # RS4
    ('ina3221', '0x42:2', 'pp1800_vio18_u', 1.8, 0.020, 'rem', True), # RS9
    ('ina3221', '0x43:0', 'pp3300_ts',      3.3, 0.020, 'rem', True), # RS17
    ('ina3221', '0x43:1', 'pp1800_h1_g',    1.8, 0.020, 'rem', True), # RS13
    ('ina3221', '0x43:2', 'pp1800_ec_vcc',  1.8, 0.020, 'rem', True), # RS19
    ('ina219',  '0x44',   'pp3300_wlan',    3.3, 0.020, 'rem', True), # RS14
    ('ina219',  '0x45',   'pp3300_u',       3.3, 0.020, 'rem', True), # RS8
    ('ina219',  '0x46',   'pp3300_ec_g',    3.3, 0.020, 'rem', True)  # RS18
]
