# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', (1,3),   'ppvar_kb_bl',     7.6, 0.100, 'j2', True), # D36
    ('sweetberry', (2,4),   'pp3300_a_micvdd', 3.3, 0.010, 'j2', True), # RA6
    ('sweetberry', (1,3),   'pp3300_g',        3.3, 0.100, 'j4', True), # PR17, original 0.005ohm
    ('sweetberry', (2,4),   'pp3300_h1',       3.3, 0.500, 'j4', True), # R423
    ('sweetberry', (6,8),   'pp3300_ec',       3.3, 0.500, 'j4', True), # R415
    ('sweetberry', (7,9),   'pp3300_tcpc',     3.3, 0.100, 'j4', True), # R416, original 0.010ohm
    ('sweetberry', (11,13), 'pp3300_hp_vbat',  3.3, 0.010, 'j4', True), # RA7, connect to pp3300_g
    ('sweetberry', (12,14), 'pp3300_a',        3.3, 0.020, 'j4', True), # R203
    ('sweetberry', (16,18), 'pp3300_a_soc',    3.3, 0.100, 'j4', True), # R410
    ('sweetberry', (17,19), 'pp3300_a_wlan',   3.3, 0.020, 'j4', True), # R409
    ('sweetberry', (21,23), 'pp3300_a_ssd',    3.3, 0.020, 'j4', True), # R411
    ('sweetberry', (22,24), 'ppvar_bat',       7.6, 0.010, 'j4', True), # PRB11
    ('sweetberry', (26,28), 'pp3300_g_in',     7.6, 0.100, 'j4', True), # PR10, original 0.020ohm
    ('sweetberry', (27,29), 'pp3300_dx_wwan',  3.3, 0.500, 'j4', True), # R418, original 0.010ohm
    ('sweetberry', (31,33), 'ppvar_gt',        7.6, 0.020, 'j4', True), # PRZ78, original 0.001ohm
    ('sweetberry', (32,34), 'ppvar_sa',        7.6, 0.020, 'j4', True), # PRZ79, original 0.010ohm
    ('sweetberry', (36,38), 'ppvar_vcc',       7.6, 0.020, 'j4', True), # PRZ77, original 0.001ohm
    ('sweetberry', (37,39), 'ppvar_bl_pwr',    7.6, 0.050, 'j4', True), # F1
]
