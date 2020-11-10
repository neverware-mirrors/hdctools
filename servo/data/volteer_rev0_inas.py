# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='servod'

inas = [
#    drvname,   child,      name,               nom,  sense, mux,   is_calib
    ('ina3221', '0x40:0', 'ppvar_vccin_aux',  1.80, 0.002, 'rem', True), # R571
    ('ina3221', '0x40:1', 'pp1100_dram',      1.10, 0.002, 'rem', True), # R592
    ('ina3221', '0x40:2', 'pp3300_ssd_a',     3.30, 0.020, 'rem', True), # R276
    ('ina3221', '0x41:0', 'ppvar_vnn_bypass', 1.05, 0.010, 'rem', True), # R572
    ('ina3221', '0x41:1', 'pp1050_a_bypass',  1.05, 0.010, 'rem', True), # R573
    ('ina3221', '0x41:2', 'pp1800_a',         1.80, 0.010, 'rem', True), # R526
    ('ina3221', '0x42:0', 'pp3300_a',         3.30, 0.005, 'rem', True), # R532
    ('ina3221', '0x42:1', 'pp3300_g',         3.30, 0.010, 'rem', True), # R518
    ('ina3221', '0x42:2', 'pp5000_a',         5.00, 0.002, 'rem', True), # R527
    ('ina3221', '0x43:0', 'pp3300_wwan_dx',   3.30, 0.010, 'rem', True), # R385
    ('ina3221', '0x43:1', 'pp3300_wlan_a',    3.30, 0.020, 'rem', True), # R645
    ('ina3221', '0x43:2', 'pp3300_edp_dx',    3.30, 0.020, 'rem', True), # R648
]
