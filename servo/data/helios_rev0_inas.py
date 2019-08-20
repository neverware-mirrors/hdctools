# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='servod'

inas = [('ina3221', '0x40:0', 'pp3300_g',             3.30, 0.005, 'rem', True),
        ('ina3221', '0x40:1', 'pp5000_a',             5.00, 0.002, 'rem', True),
        ('ina3221', '0x40:2', 'pp1800_a',             1.80, 0.010, 'rem', True),
        ('ina3221', '0x41:0', 'ppvar_vprim_core_a',   0.75, 0.002, 'rem', True),
        ('ina3221', '0x41:1', 'pp950_vccio',          0.95, 0.005, 'rem', True),
        ('ina3221', '0x41:2', 'pp1050_a',             1.05, 0.002, 'rem', True),
        ('ina3221', '0x42:0', 'pp3300_a',             3.30, 0.020, 'rem', True),
        ('ina3221', '0x42:1', 'pp3300_wlan_a',        3.30, 0.020, 'rem', True),
        ('ina3221', '0x42:2', 'pp3300_soc_a',         3.30, 0.100, 'rem', True),
        ('ina3221', '0x43:0', 'pp3300_panel_dx',      3.30, 0.020, 'rem', True),
        ('ina3221', '0x43:1', 'pp3300_ec',            3.30, 0.500, 'rem', True),
        ('ina3221', '0x43:2', 'pp1800_dram_u',        1.80, 0.220, 'rem', True)]
