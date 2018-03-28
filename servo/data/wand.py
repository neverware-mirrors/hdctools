# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
        ('ina3221', '0x40:0', 'pp3300_sys',    3.3, 0.020, 'rem', True),
        ('ina3221', '0x40:1', 'pp3300_bec',    3.3, 0.020, 'rem', True),
        ('ina3221', '0x40:2', 'pp3300_tp',     3.3, 0.020, 'rem', True),
        ('ina219',  '0x44',   'ppvar_ldo_in',  3.3, 1.000, 'rem', True),
        ('ina219',  '0x48',   'ppvar_pwr_in', 20.0, 0.010, 'rem', True),
]
