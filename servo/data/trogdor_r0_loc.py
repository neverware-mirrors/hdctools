# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', '0x40:3', 'PPVAR_BAT',          8.05, 0.010, 'j2', True), # R172_33
    ('sweetberry', '0x40:1', 'PP3300_HUB',       8.05, 0.100, 'j2', True), # R108
    ('sweetberry', '0x40:2', 'PP5000_A',           5.00, 0.010, 'j2', True), # R4689, orginal size 0.002
    ('sweetberry', '0x40:0', 'PP3300_A_R',         3.30, 0.010, 'j2', True), # R4699, orginal size 0.002
    ('sweetberry', '0x41:3', 'PP3300_EC_STBY',     3.30, 0.010, 'j2', True), # R297_FF
    ('sweetberry', '0x41:1', 'PP3300_H1',          3.30, 0.010, 'j2', True), # R296_FF
    ('sweetberry', '0x41:2', 'PP1800_VR',          3.30, 0.010, 'j2', True), # R312
    ('sweetberry', '0x41:0', 'PP1800_EC',          3.30, 0.010, 'j2', True), # R330
    ('sweetberry', '0x42:3', 'PP1800_SENSORS',     3.30, 0.010, 'j2', True), # R43
    ('sweetberry', '0x42:1', 'PP3300_PD_EC',       3.30, 0.100, 'j2', True), # R297
    ('sweetberry', '0x42:2', 'PP3300_PD_A',        3.30, 0.100, 'j2', True), # R397_FF
    ('sweetberry', '0x42:0', 'PP3300_EC',          3.30, 0.100, 'j2', True), # R398_FF
    ('sweetberry', '0x43:3', 'PP1200_TCPC_C0',     3.30, 0.010, 'j2', True), # R268
    ('sweetberry', '0x43:1', 'LCD_BL_VOUT',        3.30, 0.010, 'j2', True), # R227
    ('sweetberry', '0x43:2', 'PP3300_TCPC_C0',     3.30, 0.100, 'j2', True), # R138
    ('sweetberry', '0x43:0', 'PPVAR_BAT_R',        3.30, 0.100, 'j2', True), # Across battery
]