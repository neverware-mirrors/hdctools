# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [('ina219', 0x41, 'pp3300_s',        3.3, 0.010, 'rem', True),
        ('ina219', 0x44, 'ppvar_vcc2',      7.6, 0.010, 'rem', True),
        ('ina219', 0x45, 'ppvar_sa',        7.6, 0.010, 'rem', True),
        ('ina219', 0x46, 'ppvar_vcc1',      7.6, 0.010, 'rem', True),
        ('ina219', 0x47, 'ppvar_pwr_in',   20.0, 0.020, 'rem', True),
        ('ina219', 0x48, 'ppvar_gt',        7.6, 0.010, 'rem', True),
        ('ina219', 0x4a, 'pp3300_dx_wlan',  3.3, 0.010, 'rem', True),
        ('ina219', 0x4b, 'ppvar_bl_pwr',    7.6, 0.000, 'rem', False),
        ('ina219', 0x4c, 'pp3300_dx_edp',   3.3, 0.010, 'rem', True),
        ('ina219', 0x4d, 'pp3300_dsw_ec',   3.3, 0.010, 'rem', True)]
