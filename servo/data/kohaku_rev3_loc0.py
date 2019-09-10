# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', '0x40:3', 'pp1050_a',           1.05, 0.010, 'j2', True), # R462, SOC
    ('sweetberry', '0x40:1', 'pp1050_st',          1.05, 0.010, 'j2', True), # R665
    ('sweetberry', '0x40:2', 'pp1050_stg',         1.05, 0.010, 'j2', True), # R664
    ('sweetberry', '0x40:0', 'pp1200_dram_u',      1.20, 0.010, 'j2', True), # R463
    ('sweetberry', '0x41:3', 'pp1800_a',           1.80, 0.010, 'j2', True), # R556, SOC + audio
    ('sweetberry', '0x41:1', 'pp3300_a',           3.30, 0.010, 'j2', True), # R478
    ('sweetberry', '0x41:2', 'pp3300_cam_a',       3.30, 0.010, 'j2', True), # R482
    ('sweetberry', '0x41:0', 'pp3300_ec',          3.30, 0.500, 'j2', True), # R474, originally 0.01 Ohm
    ('sweetberry', '0x42:3', 'pp3300_g',           3.30, 0.010, 'j2', True), # R458
    ('sweetberry', '0x42:1', 'pp3300_h1_g',        3.30, 0.500, 'j2', True), # R473, originally 0.01 Ohm
    ('sweetberry', '0x42:2', 'pp3300_hp_vbat',     3.30, 0.500, 'j2', True), # R260, originally 0 Ohm
    ('sweetberry', '0x42:0', 'pp3300_panel_dx',    3.30, 0.010, 'j2', True), # R476
    ('sweetberry', '0x43:3', 'pp3300_rtc',         3.30, 0.010, 'j2', True), # R472
    ('sweetberry', '0x43:1', 'pp3300_soc_a',       3.30, 0.100, 'j2', True), # R480, originally 0.01 Ohm
    ('sweetberry', '0x43:2', 'pp3300_ssd_a',       3.30, 0.010, 'j2', True), # R708
    ('sweetberry', '0x43:0', 'pp3300_tcpc_g',      3.30, 0.100, 'j2', True), # R475, originally 0.01 Ohm
    ('sweetberry', '0x44:3', 'pp3300_trackpad_a',  3.30, 0.010, 'j3', True), # R483
    ('sweetberry', '0x44:1', 'pp3300_tsp_dig_dx',  3.30, 0.010, 'j3', True), # R670
    ('sweetberry', '0x44:2', 'pp3300_wlan_a',      3.30, 0.010, 'j3', True), # R479
    ('sweetberry', '0x44:0', 'pp5000_a',           5.00, 0.010, 'j3', True), # R459, USB
    ('sweetberry', '0x45:3', 'pp950_vccio',        0.95, 0.010, 'j3', True), # R461
    ('sweetberry', '0x45:1', 'ppvar_bat',          7.70, 0.010, 'j3', True), # R569
    ('sweetberry', '0x45:2', 'ppvar_elv_in',       7.70, 0.010, 'j3', True), # R717
    ('sweetberry', '0x45:0', 'ppvar_elvdd',        4.60, 0.010, 'j3', True), # L12, originally 0 Ohm
    ('sweetberry', '0x46:3', 'ppvar_gt',           1.52, 0.020, 'j3', True), # U143, originally 0 Ohm
    ('sweetberry', '0x46:1', 'ppvar_sa',           1.52, 0.020, 'j3', True), # U144, originally 0 Ohm
    ('sweetberry', '0x46:2', 'ppvar_vcc',          1.52, 0.020, 'j3', True), # U141, originally 0 Ohm
    ('sweetberry', '0x46:0', 'ppvar_vprim_core_a', 1.05, 0.010, 'j3', True), # R460
]
