# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [('ina3221', '0x40:0', 'pp1000_a_pmic',       7.6, 0.000, 'rem', False), # ppvar_sys_pmic_v1
        ('ina3221', '0x40:1', 'pp1000_a',            1.0, 0.005, 'rem', True),
        ('ina3221', '0x40:2', 'pp1800_a_pmic',       3.3, 0.000, 'rem', False), # vinvr2_650830
        ('ina3221', '0x41:0', 'pp1800_a',            1.8, 0.000, 'rem', False),
        ('ina3221', '0x41:1', 'pp3300_dsw_pmic',     7.6, 0.010, 'rem', True), # ppvar_sys_pmic_v3
        ('ina3221', '0x41:2', 'pp3300_dsw',          3.3, 0.005, 'rem', True),
        ('ina3221', '0x42:0', 'pp1200_vddq_pmic',    7.6, 0.000, 'rem', False), # ppvar_sys_pmic_v4
        ('ina3221', '0x42:1', 'pp1200_vddq',         1.2, 0.005, 'rem', True),
        ('ina3221', '0x42:2', 'pp5000_a_pmic',       7.6, 0.010, 'rem', True), # ppvar_sys_pmic_v5
        ('ina3221', '0x43:0', 'pp5000_a',            5.0, 0.005, 'rem', True),
        ('ina3221', '0x43:1', 'pp0600_ddrvtt_pmic',  1.2, 0.000, 'rem', False), # pp1200_vddq_ddrvttin
        ('ina3221', '0x43:2', 'pp0600_ddrvtt',       0.6, 0.000, 'rem', False),
        ('ina219',  '0x44',   'ppvar_vcc2',          7.6, 0.010, 'rem', True),
        ('ina219',  '0x45',   'ppvar_sa',            7.6, 0.010, 'rem', True),
        ('ina219',  '0x46',   'ppvar_vcc1',          7.6, 0.010, 'rem', True),
        ('ina219',  '0x47',   'ppvar_pwr_in',       20.0, 0.020, 'rem', True),
        ('ina219',  '0x48',   'ppvar_gt',            7.6, 0.010, 'rem', True),
        ('ina219',  '0x49',   'pp3300_s',            3.3, 0.010, 'rem', True),
        ('ina219',  '0x4a',   'pp3300_dx_wlan',      3.3, 0.010, 'rem', True),
        ('ina219',  '0x4b',   'ppvar_bl_pwr',        7.6, 0.000, 'rem', False),
        ('ina219',  '0x4c',   'pp3300_dx_edp',       3.3, 0.010, 'rem', True),
        ('ina219',  '0x4d',   'pp3300_dsw_ec',       3.3, 0.010, 'rem', True)]
