# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Created using go/sense-point-template

config_type='sweetberry'

inas = [
    ('sweetberry', '0x40:3', 'ppvar_sys_gpu_gfx',      13.5 , 0.001, 'j2', True), # PRV94
    ('sweetberry', '0x40:1', 'ppvar_sys_gpu_soc',      13.5 , 0.001, 'j2', True), # PRZ95
    ('sweetberry', '0x40:2', 'ppvar_sys_gpu_hbm',      13.5 , 0.001, 'j2', True), # PRY91
    ('sweetberry', '0x40:0', 'ppvar_sys_900a_gpu_hbm', 13.5 , 0.01 , 'j2', True), # PRZ96
    ('sweetberry', '0x41:3', 'pp3300a_gpu',             3.3 , 0.01 , 'j2', True), # RV394
    ('sweetberry', '0x41:1', 'ppvar_sys_900a_gpu',     13.5 , 0.01 , 'j2', True), # PR911
    ('sweetberry', '0x41:2', 'ppvar_prim_core',         0.85, 0.002, 'j2', True), # PR72
    ('sweetberry', '0x41:0', 'pp1050_a',                1.05, 0.002, 'j2', True), # PR57
    ('sweetberry', '0x42:3', 'pp950_vccio',             0.95, 0.005, 'j2', True), # PR89
    ('sweetberry', '0x42:1', 'pp2500_dram',             2.5 , 0.2  , 'j2', True), # PRM9
    ('sweetberry', '0x42:2', 'pp1200_vddq',             1.2 , 0.002, 'j2', True), # PRM14
    ('sweetberry', '0x42:0', 'pp600_vtt',               0.6 , 0.01 , 'j2', True), # PRM17
    ('sweetberry', '0x43:3', 'pp3300_g',                3.3 , 0.005, 'j2', True), # PR17
    ('sweetberry', '0x43:1', 'pp33_2500_gpu_hbm',       3.3 , 0.01 , 'j2', True), # PR2508
    ('sweetberry', '0x43:2', 'pp33_1800a_gpu',          3.3 , 0.01 , 'j2', True), # PR1807
    ('sweetberry', '0x43:0', 'pp3300_ec',               3.3 , 0.5  , 'j2', True), # R415
    ('sweetberry', '0x44:3', 'pp3300_tcpc',             3.3 , 0.01 , 'j3', True), # R416
    ('sweetberry', '0x44:1', 'pp3300_h1',               3.3 , 0.5  , 'j3', True), # R423
    ('sweetberry', '0x44:2', 'pp3300_wlan',             3.3 , 0.02 , 'j3', True), # R409
    ('sweetberry', '0x44:0', 'pp3300_dx_edp',           3.3 , 0.02 , 'j3', True), # R417
    ('sweetberry', '0x45:3', 'pp5000_a',                5.0 , 0.002, 'j3', True), # PR506
    ('sweetberry', '0x45:1', 'pp1800_a',                1.8 , 0.01 , 'j3', True), # PR38
    ('sweetberry', '0x45:2', 'ppvar_vbus_in',          20.0 , 0.01 , 'j3', True), # PRB4
    ('sweetberry', '0x45:0', 'vbat',                   13.5 , 0.01 , 'j3', True), # PRB11
    ('sweetberry', '0x46:3', 'pp3300_a',                3.3 , 0.02 , 'j3', True), # R203
    ('sweetberry', '0x46:1', 'pp1800_ec',               1.8 , 0.01 , 'j3', True), # R213
    ('sweetberry', '0x46:2', 'pp3300_dx_sd',            3.3 , 0.05 , 'j3', True), # R218
    ('sweetberry', '0x46:0', 'pp3300_a_soc',            3.3 , 0.1  , 'j3', True), # R410
    ('sweetberry', '0x47:3', 'pp3300_a_ssd',            3.3 , 0.02 , 'j3', True), # R411
    ('sweetberry', '0x47:1', 'pp3300_a_cam',            3.3 , 0.1  , 'j3', True), # R412
    ('sweetberry', '0x47:2', 'pp3300_a_trackpad',       3.3 , 0.1  , 'j3', True), # R413
    ('sweetberry', '0x47:0', 'pp3300_dx_touchscreen',   3.3 , 0.01 , 'j3', True), # R595
    ('sweetberry', '0x48:3', 'pp3300_mst',              3.3 , 0.1  , 'j4', True), # R693
    ('sweetberry', '0x48:1', 'pp1100_mst',              1.1 , 0.01 , 'j4', True), # R646
    ('sweetberry', '0x48:2', 'ppvar_sys_ia',           13.5 , 0.001, 'j4', True), # PRZ77
    ('sweetberry', '0x48:0', 'ppvar_sys_gt',           13.5 , 0.001, 'j4', True), # PRZ78
    ('sweetberry', '0x49:3', 'ppvar_sys_sa',           13.5 , 0.01 , 'j4', True), # PRZ79
]
