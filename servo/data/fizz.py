# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
#        ('ina3221', '0x40:0', 'v1p00a_vr_in',     19,  0.000, 'rem', False), #JP19
        ('ina3221', '0x40:1', 'v1p00a_vr_out',    1.0, 0.001, 'rem', True), #JP18
#        ('ina3221', '0x40:2', 'v1p8a_vr_in',      19,  0.000, 'rem', False), #JP16
#        ('ina3221', '0x41:0', 'v1p8a_vr_out',     1.8, 0.000, 'rem', False), #PR214
        ('ina3221', '0x41:1', 'v3p3a_dsw_vr_in',  19 , 0.010, 'rem', True), #JP13
        ('ina3221', '0x41:2', 'v3p3a_dsw_vr_out', 3.3, 0.001, 'rem', True), #JP20
#        ('ina3221', '0x42:0', 'vddq_mem_vr_in',   19,  0.000, 'rem', False), #JP11
        ('ina3221', '0x42:1', 'vddq_mem_vr_out',  1.2, 0.001, 'rem', True), #JP3
        ('ina3221', '0x42:2', 'v5a_vr_in',        19,  0.001, 'rem', True), #JP12
        ('ina3221', '0x43:0', 'v5a_vr_out',       5.0, 0.001, 'rem', True), #JP9
#        ('ina3221', '0x43:1', 'vddq_vtt_ldo_in',  1.2, 0.000, 'rem', True), #PR192
#        ('ina3221', '0x43:2', 'vddq_vtt_ldo_out', 0.6, 0.000, 'rem', False), #JP4
        ('ina219',  '0x44',   'vcccore_vr_in',     19,  0.010, 'rem', True), #JP8
#        ('ina219',  '0x45',   'vccsa_vr_in',      19,  0.000, 'rem', False), #JP10
        ('ina219',  '0x46',   'vcccore1_vr_in',    19,  0.010, 'rem', True), #JP7
        ('ina219',  '0x47',   'ppvar_pwr_in',     19,  0.010, 'rem', True), #PR251
        ('ina219',  '0x48',   'vccgt_vr_in',      19,  0.010, 'rem', True), #JP1
]
