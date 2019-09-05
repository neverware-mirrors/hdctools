# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='servod'

inas = [('ina3221', '0x40:0', 'pp3300_dx_mcu', 3.30, 0.500, 'rem', True), # 3.3V Rail to FP MCU
        ('ina3221', '0x40:1', 'pp3300_dx_fp',  3.30, 0.500, 'rem', True), # 3.3V Rail to FP Sensor
        ('ina3221', '0x40:2', 'pp1800_dx_fp',  1.80, 0.500, 'rem', True)] # 1.8V Rail to FP Sensor
