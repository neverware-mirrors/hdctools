# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', (1,3),   'pp3300_g',       3.3, 0.005, 'j3', True), # PR17
    ('sweetberry', (2,4),   'pp3300_h1',      3.3, 0.500, 'j3', True), # R423
    ('sweetberry', (6,8),   'pp3300_ec',      3.3, 0.500, 'j3', True), # R415
    ('sweetberry', (7,9),   'pp3300_tcpc',    3.3, 0.010, 'j3', True), # R416
    ('sweetberry', (11,13), 'pp3300_hp_vbat', 3.3, 0.010, 'j3', True), # RA7, connect to pp3300_g
    ('sweetberry', (12,14), 'pp3300_a',       3.3, 0.020, 'j3', True), # R203
    ('sweetberry', (16,18), 'pp3300_a_soc',   3.3, 0.100, 'j3', True), # R410
    ('sweetberry', (17,19), 'pp3300_a_wlan',  3.3, 0.020, 'j3', True), # R409
    ('sweetberry', (21,23), 'pp3300_a_ssd',   3.3, 0.020, 'j3', True), # R411
]
