# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type  = 'sweetberry'

revs = [4]

inas = [
       #( DRV,         (PINS),  CTRL_NAME,               NOM-V, R,     MUX,  CALIB),
        ('sweetberry', (1,3),   'pp5000_a',              5.0,   0.005, 'j2', True), #R421(short) reworked
        ('sweetberry', (2,4),   'pp3300_a',              3.3,   0.005, 'j2', True), #R92(short) reworked
        ('sweetberry', (6,8),   'pp1800_a',              1.8,   0.020, 'j2', True), #R170(short) reworked
        ('sweetberry', (7,9),   'pp1200_a',              1.2,   0.020, 'j2', True), #R171(short) reworked
        ('sweetberry', (11,13), 'pp1100_vddq_s',         1.1,   0.010, 'j2', True), #R723(short) reworked
        ('sweetberry', (12,14), 'pp1050_s',              1.05,  0.020, 'j2', True), #R725(short) reworked
        ('sweetberry', (16,18), 'pp3300_pd_a',           3.3,   0.100, 'j2', True), #R384(short) reworked
        ('sweetberry', (17,19), 'pp3300_wlan_dx',        3.3,   0.020, 'j2', True), #R389(short) reworked
        ('sweetberry', (21,23), 'pp3300_edp_dx',         3.3,   0.020, 'j2', True), #R367(short) reworked
        ('sweetberry', (22,24), 'pp3300_soc_a',          3.3,   0.020, 'j2', True), #R383(short) reworked
        ('sweetberry', (26,28), 'pp3300_ec',             3.3,   0.100, 'j2', True), #R415(short) reworked
        ('sweetberry', (27,29), 'pp3300_ldo_out',        3.3,   0.100, 'j2', True), #R133(short) reworked
        ('sweetberry', (31,33), 'pp3300_touchscreen_dx', 3.3,   0.020, 'j2', True), #R369(short) reworked
        ('sweetberry', (32,34), 'ppvar_vccgi',           1.0,   0.002, 'j2', True), #Inductor L3 stood on 2mR
        ('sweetberry', (36,38), 'ppvar_vnn',             1.0,   0.005, 'j2', True), #R724(short) reworked
        ('sweetberry', (37,39), 'vbat',                  11.55, 0.010, 'j2', True), #R542
]

