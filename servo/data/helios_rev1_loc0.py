# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', '0x44:3', 'pp1800_a',            1.80, 0.010, 'j3', True), # R3914
    ('sweetberry', '0x44:1', 'pp5000_a',            5.00, 0.010, 'j3', True), # R3918, originally 0.002 Ohm
    ('sweetberry', '0x44:2', 'pp3300_g',            3.30, 0.100, 'j3', True), # R3912, originally 0.005 Ohm
    ('sweetberry', '0x44:0', 'pp3300_g_in',        11.90, 0.020, 'j3', True), # R3909
    ('sweetberry', '0x45:3', 'ppvar_vprim_core_a',  1.05, 0.010, 'j3', True), # R4023, originally 0.002 Ohm
    ('sweetberry', '0x45:1', 'pp1050_a',            1.05, 0.010, 'j3', True), # R4024, originally 0.002 Ohm
    ('sweetberry', '0x45:2', 'pp950_vccio',         0.95, 0.010, 'j3', True), # R4025, originally 0.005 Ohm
    ('sweetberry', '0x45:0', 'pp1200_dram_u',       1.20, 0.010, 'j3', True), # R4104, originally 0.002 Ohm
    ('sweetberry', '0x46:3', 'pp600_dram_u',        0.60, 0.010, 'j3', True), # R4105
    ('sweetberry', '0x46:1', 'pp1800_dram_u',       1.80, 0.010, 'j3', True), # R4103
    ('sweetberry', '0x46:2', 'ppvar_vcc1',          1.52, 0.020, 'j3', True), # L4303, originally 0 Ohm
    ('sweetberry', '0x46:0', 'ppvar_vcc2',          1.52, 0.020, 'j3', True), # L4304, originally 0 Ohm
    ('sweetberry', '0x47:3', 'ppvar_gt',            1.52, 0.020, 'j3', True), # L4302, originally 0 Ohm
    ('sweetberry', '0x47:1', 'ppvar_sa',            1.52, 0.020, 'j3', True), # L4301, originally 0 Ohm
    ('sweetberry', '0x47:2', 'pp3300_rtc',          3.30, 0.500, 'j3', True), # R4401
    ('sweetberry', '0x47:0', 'pp3300_h1_g',         3.30, 0.100, 'j3', True), # R4402
    ('sweetberry', '0x48:3', 'pp3300_ec',           3.30, 0.100, 'j4', True), # R4405
    ('sweetberry', '0x48:1', 'pp3300_tcpc_g',       3.30, 0.100, 'j4', True), # R4406
    ('sweetberry', '0x48:2', 'pp3300_panel_dx',     3.30, 0.020, 'j4', True), # R4413
    ('sweetberry', '0x48:0', 'pp3300_sd_dx',        3.30, 0.050, 'j4', True), # R4417
    ('sweetberry', '0x49:3', 'pp3300_a',            3.30, 0.020, 'j4', True), # R4407
    ('sweetberry', '0x49:1', 'pp3300_wlan_a',       3.30, 0.020, 'j4', True), # R4408
    ('sweetberry', '0x49:2', 'pp3300_soc_a',        3.30, 0.100, 'j4', True), # R4409
    ('sweetberry', '0x49:0', 'pp3300_ssd_a',        3.30, 0.010, 'j4', True), # R4410
    ('sweetberry', '0x4a:3', 'pp3300_cam_a',        3.30, 0.100, 'j4', True), # R4411
    ('sweetberry', '0x4a:1', 'pp3300_trackpad_a',   3.30, 0.100, 'j4', True), # R4412
    ('sweetberry', '0x4a:2', 'vbat',               11.90, 0.010, 'j4', True), # R3825
    ('sweetberry', '0x4a:0', 'pp1800_fp_s',         1.80, 0.500, 'j4', True), # R3126
    ('sweetberry', '0x4b:3', 'pp3300_fp',           3.30, 0.500, 'j4', True), # R3125
    ('sweetberry', '0x4b:1', 'pp3300_fp_s',         3.30, 0.500, 'j4', True), # R3127, originally 0 Ohm
]
