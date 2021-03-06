# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These devices are ina3221 (3-channels/i2c address) devices
inas = [('ina3221', '0x40:0', 'pp3300_dsw_ec',   3.3,   0.100, 'rem', True),
        ('ina3221', '0x40:1', 'pp3300_dx_wlan',  3.3,   0.057, 'rem', True),
        ('ina3221', '0x40:2', 'pp3300_dx_edp',   3.3,   0.100, 'rem', True),
        ('ina3221', '0x41:0', 'pp3300_dsw',      3.3,   0.100, 'rem', True),
        ('ina3221', '0x41:1', 'pp5000_a',        5.0,   0.016, 'rem', True),
        ('ina3221', '0x41:2', 'pp3300_a',        3.3,   0.01875, 'rem', True),
        ('ina3221', '0x42:0', 'pp1800_a',        1.8,   0.100, 'rem', True),
        ('ina3221', '0x42:1', 'pp1800_dram',     1.8,   0.100, 'rem', True),
        ('ina3221', '0x42:2', 'pp1200_vddq',     1.2,   0.007, 'rem', True),
        ('ina3221', '0x43:0', 'pp1000_a',        1.0,   0.01755, 'rem', True),
        ('ina3221', '0x43:1', 'pp975_io',        0.975, 0.018, 'rem', True),
        ('ina3221', '0x43:2', 'pp850_prim_core', 0.850, 0.016, 'rem', True)]
