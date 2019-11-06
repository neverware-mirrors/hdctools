# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='servod'

inas = [('ina3221', '0x40:0', 'pp3300_g',             3.30, 0.005, 'rem', True), # R394, Global power rail
        ('ina3221', '0x40:1', 'pp5000_a',             5.00, 0.002, 'rem', True), # R393, Primary rail
        ('ina3221', '0x40:2', 'pp3300_wlan_a',        3.30, 0.020, 'rem', True), # R483
        ('ina3221', '0x42:0', 'pp3300_a',             3.30, 0.020, 'rem', True), # R482
        ('ina3221', '0x42:1', 'pp3300_ssd_dx',        3.30, 0.010, 'rem', True), # R478
        ('ina3221', '0x42:2', 'pp3300_lan_a',         3.30, 0.050, 'rem', True), # R484
        ('ina3221', '0x43:1', 'pp1200_dram_u',        1.20, 0.002, 'rem', True), # R431 VTT
        ('ina3221', '0x43:2', 'pp2500_dram_u',        2.50, 0.200, 'rem', True), # R430 VPP
]
