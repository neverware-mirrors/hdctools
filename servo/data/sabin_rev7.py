# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Created using go/sense-point-template
# Link: go/sabin-sense-point

config_type='sweetberry'

inas = [
    ('sweetberry', '0x40:3', 'vbat',         11.40, 0.010, 'j2', True), # VBAT
    ('sweetberry', '0x40:1', 'pp3300_ec',     3.30, 2.200, 'j2', True), # RE4
    ('sweetberry', '0x40:2', 'pp3300_wlan',   3.30, 0.020, 'j2', True), # RW9
    ('sweetberry', '0x40:0', 'pp3300_a',      3.30, 0.020, 'j2', True), # PL403
    ('sweetberry', '0x41:3', 'pp1800_emmc',   1.80, 2.200, 'j2', True), # R183
    ('sweetberry', '0x41:1', 'pp5000_a',      5.00, 0.020, 'j2', True), # PL404
    ('sweetberry', '0x41:2', 'pp1200_ddr',    1.20, 0.100, 'j2', True), # PL603
    ('sweetberry', '0x41:0', 'ppvar_bl',     11.40, 0.010, 'j2', True), # R290
    ('sweetberry', '0x42:3', 'pp3300_dx_edp', 3.30, 0.010, 'j2', True), # R292
    ('sweetberry', '0x42:1', 'pp3300_touchp', 3.30, 0.100, 'j2', True), # R227
#   ('sweetberry', '0x42:2', 'unused',        0.00, 0.000, 'j2', True),
    ('sweetberry', '0x42:0', 'pp5000_touchs', 5.00, 0.100, 'j2', True), # R148
    ('sweetberry', '0x43:3', 'pp3300_camera', 3.30, 0.100, 'j2', True), # R142
    ('sweetberry', '0x43:1', 'ppvar_vcc',     1.15, 0.002, 'j2', True), # PL601
    ('sweetberry', '0x43:2', 'ppvar_vgg',     1.15, 0.002, 'j2', True), # PL602
    ('sweetberry', '0x43:0', 'ppvar_vnn',     1.05, 0.005, 'j2', True), # PL501
]
