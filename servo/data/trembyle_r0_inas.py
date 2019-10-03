# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These devices are ina3221 (3-channels/i2c address) devices
inas = [
#    drvname,   slv,      name,                 nom,   sense, mux,   is_calib
    ('ina3221', '0x40:0', 'pp3300_alw',         3.300, 0.002, 'rem', True),
    ('ina3221', '0x40:1', 'pp5000_a',           5.000, 0.002, 'rem', True),
    ('ina3221', '0x40:2', 'pp1800_alw',         1.800, 0.002, 'rem', True),

    ('ina3221', '0x41:0', 'pp1200_vddq_cs',     1.200, 0.005, 'rem', True),
    ('ina3221', '0x41:1', 'ppvar_vddcr_soc_cs', 1.000, 0.005, 'rem', True),
    ('ina3221', '0x41:2', 'ppvar_vddcr_cs',     1.000, 0.005, 'rem', True),

    ('ina3221', '0x42:0', 'pp900_vddp_s0',      0.900, 0.002, 'rem', True),
    ('ina3221', '0x42:1', 'ppvar_sys_db',       0.000, 0.020, 'rem', True),
    ('ina3221', '0x42:2', 'pp900_vddp_a',       0.900, 0.005, 'rem', True),

    ('ina3221', '0x43:0', 'pp3300_wifi',        3.300, 0.020, 'rem', True),
    ('ina3221', '0x43:1', 'pp3300_edp',         3.300, 0.020, 'rem', True),
    ('ina3221', '0x43:2', 'ppvar_bl',           0.000, 0.020, 'rem', True),
]
