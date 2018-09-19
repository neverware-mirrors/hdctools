# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('sweetberry', '0x40:3', 'ppvar_vcc',          1.0, 0.002, 'j2', True),
    ('sweetberry', '0x40:1', 'ppvat_gt',           1.0, 0.002, 'j2', True),
    ('sweetberry', '0x40:2', 'ppvar_sa',           1.0, 0.010, 'j2', True),
    ('sweetberry', '0x40:0', 'pp3300_a_emmc',      3.3, 0.100, 'j2', True),
    ('sweetberry', '0x41:3', 'pp1800_a_emmc',      1.8, 0.100, 'j2', True),
    ('sweetberry', '0x41:1', 'pp3300_dsw',         3.3, 0.010, 'j2', True),
    ('sweetberry', '0x41:2', 'pp3300_a',           3.3, 0.010, 'j2', True),
    ('sweetberry', '0x42:0', 'pp3300_dx_wlan',     3.3, 0.010, 'j2', True),
    ('sweetberry', '0x43:3', 'ppvar_bl_vcc',       7.7, 0.500, 'j2', True),
    ('sweetberry', '0x43:1', 'pp3300_dx_trackpad', 3.3, 0.100, 'j2', True),
    ('sweetberry', '0x43:2', 'pp3300_h1',          3.3, 0.100, 'j2', True),
    ('sweetberry', '0x43:0', 'vbat',               7.7, 0.020, 'j2', True),
]
