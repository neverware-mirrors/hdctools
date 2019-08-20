# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

revs = [6]

inas = [
    ('sweetberry', '0x40:3', 'pp975_io',        7.7, 0.100, 'j2', True), # R111
    ('sweetberry', '0x40:1', 'pp850_prim_core', 7.7, 0.100, 'j2', True), # R164
    ('sweetberry', '0x40:2', 'pp3300_dsw',      3.3, 0.010, 'j2', True), # R513
    ('sweetberry', '0x40:0', 'pp3300_a',        7.7, 0.010, 'j2', True), # R144
    ('sweetberry', '0x41:3', 'pp1800_a',        7.7, 0.100, 'j2', True), # R141
    ('sweetberry', '0x41:1', 'pp1800_u',        7.7, 0.100, 'j2', True), # R161
    ('sweetberry', '0x41:2', 'pp1200_vddq',     7.7, 0.100, 'j2', True), # R162
    ('sweetberry', '0x41:0', 'pp1000_a',        7.7, 0.100, 'j2', True), # R163
    ('sweetberry', '0x42:3', 'pp3300_dx_wlan',  3.3, 0.010, 'j2', True), # R645
    ('sweetberry', '0x42:1', 'pp3300_dx_edp',   3.3, 0.010, 'j2', True), # F1
    ('sweetberry', '0x42:2', 'vbat',            7.7, 0.010, 'j2', True), # R226
    ('sweetberry', '0x42:0', 'ppvar_vcc',       1.0, 0.003, 'j2', True), # L13
    ('sweetberry', '0x43:3', 'ppvar_sa',        1.0, 0.005, 'j2', True), # L12
    ('sweetberry', '0x43:1', 'ppvar_gt',        1.0, 0.003, 'j2', True), # L31
    ('sweetberry', '0x43:2', 'ppvar_bl',        7.7, 0.050, 'j2', True), # U89
    ('sweetberry', '0x43:0', 'ppvar_vbus_in',  15.0, 0.020, 'j2', True), # R213
]
