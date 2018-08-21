# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

# the names j2, j3, and j4 are the white banks on sweetberry
# Note that here the bank name in the mux position is optional
# as it only gets used to generate a docstring help message
inas = [
    ('sweetberry', '0x40:3', 'pp975_io'       , 7.7, 0.100, 'j2', True), # R111
    ('sweetberry', '0x40:1', 'pp850_prim_core', 0.9, 0.010, 'j2', True), # R292 TP93  TP94
    ('sweetberry', '0x40:2', 'pp3300_dsw'     , 3.3, 0.010, 'j2', True), # R513 TP84  TP132
    ('sweetberry', '0x40:0', 'pp3300_a'       , 3.3, 0.005, 'j2', True), # R288
    ('sweetberry', '0x41:3', 'pp1800_a'       , 1.8, 0.010, 'j2', True), # R423 TP85  TP86
    ('sweetberry', '0x41:1', 'pp1800_u'       , 1.8, 0.010, 'j2', True), # R286 TP78  TP79
    ('sweetberry', '0x41:2', 'pp1200_vddq'    , 1.2, 0.005, 'j2', True), # R291 TP313 TP285
    ('sweetberry', '0x41:0', 'pp1000_a'       , 1.0, 0.005, 'j2', True), # R290 TP95  TP96
    ('sweetberry', '0x42:3', 'pp3300_h1'      , 3.3, 0.100, 'j2', True), # R390 TP222 TP221
    ('sweetberry', '0x42:1', 'ppvar_bl'       , 3.1, 0.050, 'j2', True), # R95  TP202 TP2
    ('sweetberry', '0x42:2', 'ppvar_pogo'     , 7.7, 0.200, 'j2', True), # R25  TP160 TP161
    ('sweetberry', '0x42:0', 'vbat'           , 7.7, 0.010, 'j2', True), # R226 TP148 TP140
    ('sweetberry', '0x43:3', 'pp3300_fpmcu'   , 3.3, 0.100, 'j2', True), # R646 TP76  TP77
#   ('sweetberry', '0x43:1', 'Unused'         , x.x, 0.xxx, 'j2', True),
    ('sweetberry', '0x43:2', 'pp3300_dx_edp'  , 3.3, 0.010, 'j2', True), # R644 TP80  TP87
    ('sweetberry', '0x43:0', 'pp3300_dx_touch', 3.3, 0.100, 'j2', True), # R324 TP71  TP75
    ('sweetberry', '0x44:3', 'ppvar_vcc1'     , 1.0, 0.005, 'j3', True), # L13
    ('sweetberry', '0x44:1', 'ppvar_vcc2'     , 1.0, 0.005, 'j3', True), # L38
    ('sweetberry', '0x44:2', 'ppvat_gt'       , 1.0, 0.005, 'j3', True), # L31
    ('sweetberry', '0x44:0', 'ppvar_sa'       , 1.0, 0.005, 'j3', True), # L12
    ('sweetberry', '0x45:3', 'pp3300_a_vr'    , 7.7, 0.010, 'j3', True), # R144
    ('sweetberry', '0x45:1', 'pp3300_dsw_ec'  , 3.3, 0.100, 'j3', True), # R54  TP226 TP227
    ('sweetberry', '0x45:2', 'pp3300_dsw_db0' , 3.3, 0.100, 'j3', True), # R33  TP276 TP218
    ('sweetberry', '0x45:0', 'pp3300_dsw_db1' , 3.3, 0.100, 'j3', True), # R44  TP208 TP220
    ('sweetberry', '0x46:3', 'pp3300_dx_wlan' , 3.3, 0.010, 'j3', True), # R645
]
