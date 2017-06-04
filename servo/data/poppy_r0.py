# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
        ('ina3221', '0x40:0', 'pp3300_dsw_ec',    3.3, 1.000, 'rem', True),
        ('ina3221', '0x40:1', 'pp3300_dx_wlan',   3.3, 0.050, 'rem', True),
        ('ina3221', '0x40:2', 'pp3300_dx_edp',    3.3, 0.100, 'rem', True),
        ('ina3221', '0x41:0', 'pp3300_dsw',       3.3, 0.020, 'rem', True),
        ('ina3221', '0x41:1', 'pp5000_a',         5.0, 0.010, 'rem', True),
        ('ina3221', '0x41:2', 'pp3300_a',         3.3, 0.010, 'rem', True),
        ('ina3221', '0x42:0', 'pp1800_a',         1.8, 0.000, 'rem', False),
        ('ina3221', '0x42:1', 'pp1800_u_dram',    1.8, 0.000, 'rem', False),
        ('ina3221', '0x42:2', 'pp1200_vddq',      1.2, 0.000, 'rem', False),
        ('ina3221', '0x43:0', 'pp1000_a',         1.0, 0.000, 'rem', False),
        ('ina3221', '0x43:1', 'pp975_io',       0.975, 0.000, 'rem', False),
        ('ina3221', '0x43:2', 'pp850_prim_core', 0.85, 0.000, 'rem', False),
        ('ina219',  '0x44',   'ppvar_gt_vin',     5.0, 0.000, 'rem', False),
        ('ina219',  '0x45',   'ppvar_sa_vin',     5.0, 0.000, 'rem', False),
        ('ina219',  '0x46',   'ppvar_vcc_vin',    5.0, 0.000, 'rem', False),
        ('ina219',  '0x47',   'ppvar_pwr_in_bb', 12.0, 0.020, 'rem', True),
        ('ina219',  '0x48',   'ppvar_batt_r',    12.0, 0.010, 'rem', True),
        ('ina219',  '0x49',   'pp3300_dx_base',   3.3, 0.020, 'rem', True),
]
