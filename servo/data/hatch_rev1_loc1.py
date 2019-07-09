# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', '0x44:3', 'vbat',                 7.60, 0.010, 'j3', True), # PRB11
    ('sweetberry', '0x44:1', 'pp1050_a',             1.05, 0.010, 'j3', True), # PR57, Primary rail, original 0.002ohm
    ('sweetberry', '0x44:2', 'pp1200_vddq',          1.20, 0.010, 'j3', True), # PRM14, Processor and Memory power rail, original 0.002ohm
    ('sweetberry', '0x44:0', 'pp1800_a',             1.80, 0.010, 'j3', True), # PR38, Primary rail
    ('sweetberry', '0x45:3', 'pp2500_dram',          2.50, 0.200, 'j3', True), # PRM9, Memory power rail
    ('sweetberry', '0x45:1', 'pp3300_a',             3.30, 0.020, 'j3', True), # R203, Primary rail
    ('sweetberry', '0x45:2', 'pp3300_a_soc',         3.30, 0.100, 'j3', True), # R410
    ('sweetberry', '0x45:0', 'pp3300_a_ssd',         3.30, 0.020, 'j3', True), # R411
    ('sweetberry', '0x46:3', 'pp3300_a_wlan',        3.30, 0.020, 'j3', True), # R409
    ('sweetberry', '0x46:1', 'pp3300_dx_edp',        3.30, 0.020, 'j3', True), # R417, Panel power rail
    ('sweetberry', '0x46:2', 'pp3300_dx_wwan',       3.30, 0.500, 'j3', True), # R418, original 0.010ohm
    ('sweetberry', '0x46:0', 'pp3300_ec',            3.30, 0.500, 'j3', True), # R415
    ('sweetberry', '0x47:3', 'pp3300_g',             3.30, 0.100, 'j3', True), # PR17, Global power rail, original 0.005ohm
    ('sweetberry', '0x47:1', 'pp3300_g_in',          7.60, 0.100, 'j3', True), # PR10, original 0.020ohm
    ('sweetberry', '0x47:2', 'pp3300_h1',            3.30, 0.500, 'j3', True), # R423
    ('sweetberry', '0x47:0', 'pp3300_hp_vbat',       3.30, 0.010, 'j3', True), # RA7
    ('sweetberry', '0x48:3', 'pp3300_tcpc',          3.30, 0.100, 'j4', True), # R416, original 0.010ohm
    ('sweetberry', '0x48:1', 'pp5000_a',             5.00, 0.010, 'j4', True), # PR506, Primary rail, original 0.002ohm
    ('sweetberry', '0x48:2', 'pp950_vccio',          0.95, 0.010, 'j4', True), # PR89, IO power rail, original 0.005ohm
    ('sweetberry', '0x48:0', 'ppvar_a_vccprim_core', 7.60, 0.010, 'j4', True), # PR72, PCH Core rail (Primary Well), original 0.002ohm
    ('sweetberry', '0x49:3', 'ppvar_bl_pwr',         7.60, 0.050, 'j4', True), # F1, no original resistor
    ('sweetberry', '0x49:1', 'ppvar_gt',             7.60, 0.020, 'j4', True), # PRZ78, original 0.001ohm
    ('sweetberry', '0x49:2', 'ppvar_kb_bl',          7.60, 0.100, 'j4', True), # D36, no original resistor
    ('sweetberry', '0x49:0', 'ppvar_sa',             7.60, 0.020, 'j4', True), # PRZ79, original 0.010ohm
    ('sweetberry', '0x4a:3', 'ppvar_vcc',            7.60, 0.020, 'j4', True), # PRZ77, original 0.001ohm
]
