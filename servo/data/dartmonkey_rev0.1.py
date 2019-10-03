# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These devices are ina3221 (3-channels/i2c address) devices
inas = [
    # Sensor rails
    ('ina3221', '0x40:0', 'pp1800_fpc',  1.8, 3.300, 'rem', True),
    ('ina3221', '0x40:1', 'pp3300_elan', 3.3, 2.200, 'rem', True),
    ('ina3221', '0x40:2', '_disconn0',   3.3, 0.100, 'rem', False),
    # MCU rails
    ('ina3221', '0x41:0', 'pp3300_h7',   3.3, 0.240, 'rem', True),
    ('ina3221', '0x41:1', 'pp3300_f4',   3.3, 0.500, 'rem', True),
    ('ina3221', '0x41:2', '_disconn1',   3.3, 0.100, 'rem', False),
]
