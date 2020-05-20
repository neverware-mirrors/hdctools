# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='servod'

revs = [ 0 ]

inas = [
#    drvname,   slv,      name,            nom,  sense, mux,   is_calib
    ('ina3221', '0x40:0', 'pp1800_brij',   1.80, 0.010, 'rem', True), # R455
    ('ina3221', '0x40:1', 'pp1200_brij',   1.20, 0.010, 'rem', True), # R93_LS
    ('ina3221', '0x40:2', 'pp3300_hub',    3.30, 0.010, 'rem', True), # R108
    ('ina3221', '0x41:0', 'pp3300_dx_edp', 3.30, 0.100, 'rem', True), # R95_LS
    ('ina3221', '0x41:1', 'pp3300_cam',    3.30, 0.100, 'rem', True), # R228
    ('ina3221', '0x41:2', 'ppvar_lcd_bl',  5.00, 0.010, 'rem', True), # R227
    ('ina3221', '0x42:0', 'pp1800_h1',     1.80, 0.010, 'rem', True), # R314
    ('ina3221', '0x42:1', 'pp3300_a',      3.30, 0.002, 'rem', True), # R4699
    ('ina3221', '0x42:2', 'pp3300_h1',     3.30, 0.010, 'rem', True), # R296_FF
    ('ina3221', '0x43:0', 'src_vph_pwr',   4.00, 0.002, 'rem', True), # R321
    ('ina3221', '0x43:1', 'pp1800_ec',     1.80, 0.010, 'rem', True), # R330
    ('ina3221', '0x43:2', 'pp3300_ec',     3.30, 0.010, 'rem', True), # R398_FF
]
