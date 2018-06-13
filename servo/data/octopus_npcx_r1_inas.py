# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These devices are ina3221 (3-channels/i2c address) devices
#        drvname,   slv,      name,              nom,  sense, mux,   is_calib
inas = [('ina3221', '0x40:0', 'pp3300_edp_dx',   3.3,  0.020, 'rem', True),
        ('ina3221', '0x40:1', 'pp5000_a',        5.0,  0.002, 'rem', True),
        ('ina3221', '0x40:2', 'pp1800_a',        1.8,  0.020, 'rem', True),
        ('ina3221', '0x41:0', 'pp1200_a',        1.2,  0.020, 'rem', True),
        ('ina3221', '0x41:1', 'pp1100_vddq_s',   1.1,  0.005, 'rem', True),
        ('ina3221', '0x41:2', 'pp1050_s',        1.05, 0.005, 'rem', True),
        # 0x42:0 only goes to test points
        ('ina3221', '0x42:1', 'pp3300_ec',       3.3,  0.100, 'rem', True),
        ('ina3221', '0x42:2', 'pp3300_soc_a',    3.3,  0.020, 'rem', True),
        ('ina3221', '0x43:0', 'pp3300_wlan_dx',  3.3,  0.020, 'rem', True),
        ('ina3221', '0x43:1', 'pp3300_a',        3.3,  0.002, 'rem', True),
        ('ina3221', '0x43:2', 'pp3300_pd_a',     3.3,  0.100, 'rem', True)]
