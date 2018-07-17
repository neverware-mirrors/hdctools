# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

# the names j2, j3, and j4 are the white banks on sweetberry
# Note that here the bank name in the mux position is optional
# as it only gets used to generate a docstring help message
inas = [
    ('sweetberry', '0x40:3', 'j2_1' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x40:1', 'j2_2' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x40:2', 'j2_3' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x40:0', 'j2_4' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x41:3', 'j2_5' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x41:1', 'j2_6' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x41:2', 'j2_7' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x41:0', 'j2_8' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x42:3', 'j2_9' , 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x42:1', 'j2_10', 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x42:2', 'j2_11', 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x42:0', 'j2_12', 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x43:3', 'j2_13', 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x43:1', 'j2_14', 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x43:2', 'j2_15', 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x43:0', 'j2_16', 5.0, 0.010, 'j2', False),
    ('sweetberry', '0x44:3', 'j3_1' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x44:1', 'j3_2' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x44:2', 'j3_3' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x44:0', 'j3_4' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x45:3', 'j3_5' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x45:1', 'j3_6' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x45:2', 'j3_7' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x45:0', 'j3_8' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x46:3', 'j3_9' , 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x46:1', 'j3_10', 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x46:2', 'j3_11', 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x46:0', 'j3_12', 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x47:3', 'j3_13', 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x47:1', 'j3_14', 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x47:2', 'j3_15', 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x47:0', 'j3_16', 5.0, 0.010, 'j3', False),
    ('sweetberry', '0x48:3', 'j4_1' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x48:1', 'j4_2' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x48:2', 'j4_3' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x48:0', 'j4_4' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x49:3', 'j4_5' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x49:1', 'j4_6' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x49:2', 'j4_7' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x49:0', 'j4_8' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x4a:3', 'j4_9' , 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x4a:1', 'j4_10', 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x4a:2', 'j4_11', 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x4a:0', 'j4_12', 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x4b:3', 'j4_13', 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x4b:1', 'j4_14', 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x4b:2', 'j4_15', 5.0, 0.010, 'j4', False),
    ('sweetberry', '0x4b:0', 'j4_16', 5.0, 0.010, 'j4', False),
]
