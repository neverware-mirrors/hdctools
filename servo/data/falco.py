# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [
    ('ina219', 0x40, 'pp5000', 5.0, 0.01, 'loc0', True),            # PL8
    ('ina219', 0x41, 'pp3300_dsw', 3.3, 0.01, 'loc0', True),        # PL9
    ('ina219', 0x42, 'pp1350', 1.35, 0.01, 'loc0', True),           # PL11
    ('ina219', 0x43, 'pp1050_pch_sus', 1.05, 0.01, 'loc0', True),   # PL13
    ('ina219', 0x44, 'pp1500', 1.5, 0.1, 'loc0', True),             # PL16
    ('ina219', 0x45, 'vin', 19, 0.01, 'loc0', True),                # PR223
    ]
