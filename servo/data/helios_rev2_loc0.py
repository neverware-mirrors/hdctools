# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', '0x44:3', 'vbat',          11.90, 0.020, 'j3', True), # R3825
    ('sweetberry', '0x44:1', 'pp1200_dram_u',  1.20, 0.010, 'j3', True), # SR4104, originally 0 Ohm
    ('sweetberry', '0x44:2', 'pp1800_dram_u',  1.80, 0.010, 'j3', True), # SR4103, originally 0 Ohm
    ('sweetberry', '0x44:0', 'pp3300_ec',      3.30, 0.100, 'j3', True), # SR4405, originally 0 Ohm
    ('sweetberry', '0x45:3', 'pp3300_soc_a',   3.30, 0.100, 'j3', True), # SR4409, originally 0 Ohm
    ('sweetberry', '0x45:1', 'pp3300_wlan_a',  3.30, 0.020, 'j3', True), # SR4408, originally 0 Ohm
]
