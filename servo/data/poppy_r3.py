# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
        ('ina3221', '0x40:0', 'pp3300_dsw_ec',    3.3, 0.010, 'rem', True),
        ('ina3221', '0x40:1', 'pp3300_dx_wlan',   3.3, 0.010, 'rem', True),
        ('ina3221', '0x40:2', 'pp3300_dx_edp',    3.3, 0.010, 'rem', True),
        ('ina3221', '0x41:0', 'pp3300_dsw',       3.3, 0.010, 'rem', True),
        ('ina3221', '0x41:1', 'pp5000_a',         5.0, 0.010, 'rem', True),
        ('ina3221', '0x41:2', 'pp3300_a',         3.3, 0.010, 'rem', True),
        ('ina3221', '0x42:0', 'pp1800_a',         1.8, 0.010, 'rem', True),
        ('ina3221', '0x42:1', 'pp1800_u_dram',    1.8, 0.010, 'rem', True),
        ('ina3221', '0x42:2', 'pp1200_vddq',      1.2, 0.010, 'rem', True),
        ('ina3221', '0x43:0', 'pp1000_a',         1.0, 0.010, 'rem', True),
        ('ina3221', '0x43:1', 'pp975_io',       0.975, 0.010, 'rem', True),
        ('ina3221', '0x43:2', 'pp850_prim_core', 0.85, 0.010, 'rem', True),
        ('ina219',  '0x44',   'pp3300_h1',        3.3, 0.010, 'rem', True),
        ('ina219',  '0x45',   'ppvar_sys_bl',     8.0, 0.010, 'rem', True),
        ('ina219',  '0x46',   'pp3300_dx_touch',  3.3, 0.010, 'rem', True),
        ('ina219',  '0x47',   'ppvar_pwr_in_bb',  8.0, 0.020, 'rem', True),
        ('ina219',  '0x48',   'ppvar_batt_r',     8.0, 0.010, 'rem', True),
        ('ina219',  '0x49',   'ppvar_dx_base',    5.0, 0.010, 'rem', True),
]
