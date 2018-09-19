# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These devices are ina3221 (3-channels/i2c address) devices
inas = [
#    drvname,   slv,      name,             nom,   sense, mux,   is_calib
    ('ina3221', '0x40:0', 'pp3300_a',       3.300, 0.020, 'rem', True),
    ('ina3221', '0x40:1', 'pp5000_a',       5.000, 0.002, 'rem', True),
    ('ina3221', '0x40:2', 'pp1800_a',       1.800, 0.020, 'rem', True),

    ('ina3221', '0x41:0', 'pp1200_vddq',    1.200, 0.005, 'rem', True),
    ('ina3221', '0x41:1', 'ppvar_vddcr_nb', 0.875, 0.005, 'rem', True),
    ('ina3221', '0x41:2', 'ppvar_vddcr',    0.850, 0.005, 'rem', True),

    ('ina3221', '0x42:0', 'pp3300_tcpc',    3.300, 0.500, 'rem', True),
    ('ina3221', '0x42:1', 'pp3300_ec_a',    3.300, 0.500, 'rem', True),
    ('ina3221', '0x42:2', 'pp950_a',        0.950, 0.005, 'rem', True),

    ('ina3221', '0x43:0', 'pp3300_wlan',    3.300, 0.020, 'rem', True),
    ('ina3221', '0x43:1', 'pp3300_edp',     3.300, 0.020, 'rem', True),
    ('ina3221', '0x43:2', 'pp950_vddp_s0',  0.950, 0.002, 'rem', True),
]
