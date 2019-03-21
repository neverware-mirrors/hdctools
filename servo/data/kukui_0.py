# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates kukui_rev0, kukui_rev1, kukui_rev2
revs = [0, 1, 2]

inas = [
        ('ina3221', '0x40:0', 'ppvar_c0_vbus',  5.0, 0.020, 'rem', True),
        ('ina3221', '0x40:1', 'ppvar_batt',     8.0, 0.020, 'rem', True),
        ('ina3221', '0x40:2', 'ppvar_pmic',     8.0, 0.020, 'rem', True),
        ('ina3221', '0x41:0', 'ppvar_bl',       8.0, 0.020, 'rem', True),
        ('ina3221', '0x41:1', 'pp3300_alw',     3.3, 0.020, 'rem', True),
        ('ina3221', '0x41:2', 'pp3300_ctp',     3.3, 0.020, 'rem', True),
        ('ina3221', '0x42:0', 'pp3300_h1',      3.3, 0.050, 'rem', True),
        ('ina3221', '0x42:1', 'ppvar_sys',      8.0, 0.020, 'rem', True),
        ('ina3221', '0x42:2', 'pp1800_alw',     1.8, 0.020, 'rem', True),
        ('ina3221', '0x43:0', 'pp3300_lcm',     3.3, 0.020, 'rem', True),
        ('ina3221', '0x43:1', 'pp1800_h1',      1.8, 0.050, 'rem', True),
        ('ina3221', '0x43:2', 'pp1800_ec',      1.8, 0.050, 'rem', True),
        ('ina219',  '0x44',   'pp3300_wlan',    3.3, 0.020, 'rem', True),
        ('ina219',  '0x45',   'pp1800_wlan',    1.8, 0.020, 'rem', True),
        ('ina219',  '0x46',   'ppvar_dram',     8.0, 0.020, 'rem', True)
]
