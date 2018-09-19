# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', '0x40:3', 'pp975_io',           7.7, 0.100, 'j2', True), # R111
    ('sweetberry', '0x40:1', 'pp850_prim_core',    7.7, 0.100, 'j2', True), # R164
    ('sweetberry', '0x40:2', 'pp3300_dsw',         3.3, 0.010, 'j2', True), # R513
    ('sweetberry', '0x40:0', 'pp3300_a',           7.7, 0.010, 'j2', True), # R144
    ('sweetberry', '0x41:3', 'pp1800_a',           7.7, 0.100, 'j2', True), # R141
    ('sweetberry', '0x41:1', 'pp1800_u',           7.7, 0.100, 'j2', True), # R161
    ('sweetberry', '0x41:2', 'pp1200_vddq',        7.7, 0.100, 'j2', True), # R162
    ('sweetberry', '0x41:0', 'pp1000_a',           7.7, 0.100, 'j2', True), # R163
    ('sweetberry', '0x42:3', 'pp3300_h1',          3.3, 0.100, 'j2', True), # R390
    ('sweetberry', '0x42:1', 'ppvar_bl',           7.7, 0.050, 'j2', True), # F1
    ('sweetberry', '0x42:2', 'pp3300_dx_wlan',     3.3, 0.010, 'j2', True), # R645
    ('sweetberry', '0x42:0', 'pp3300_dx_edp',      3.3, 0.010, 'j2', True), # R644
    ('sweetberry', '0x43:3', 'pp3300_dx_touch',    3.3, 0.100, 'j2', True), # R324
    ('sweetberry', '0x43:1', 'pp3300_dx_trackpad', 3.3, 0.100, 'j2', True), # R646
    ('sweetberry', '0x43:2', 'pp3300_dsw_ec',      3.3, 0.100, 'j2', True), # R54
    ('sweetberry', '0x43:0', 'vbat',               7.7, 0.010, 'j2', True), # R226
    ('sweetberry', '0x44:3', 'ppvar_vcc',          1.0, 0.002, 'j3', True), # L13
    ('sweetberry', '0x44:1', 'ppvar_sa',           1.0, 0.005, 'j3', True), # L12
    ('sweetberry', '0x44:2', 'ppvar_gt',           1.0, 0.002, 'j3', True), # L31
    ('sweetberry', '0x44:0', 'pp1800_dx_trackpad', 1.8, 0.100, 'j3', True), # R229
    ('sweetberry', '0x45:3', 'ppvar_kb_bl',        7.7, 0.100, 'j3', True), # L9
    ('sweetberry', '0x45:1', 'pp3300_dx_cam',      3.3, 0.100, 'j3', True), # R354
    ('sweetberry', '0x45:2', 'pp1000_st',          1.0, 0.100, 'j3', True), # R650
    ('sweetberry', '0x45:0', 'pp1000_stg',         1.0, 0.500, 'j3', True), # R649
]