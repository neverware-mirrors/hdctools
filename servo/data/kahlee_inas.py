# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# for use with servo INA adapter board.  If measuring via servo V1 this can just
# be ignored.  clobber_ok added if user wishes to include servo_loc.xml
# additionally.
inline = """
  <map>
    <name>adc_mux</name>
    <doc>valid mux values for DUT's two banks of INA219 off PCA9540
    ADCs</doc>
    <params clobber_ok="" none="0" bank0="4" bank1="5"></params>
  </map>
  <control>
    <name>adc_mux</name>
    <doc>4 to 1 mux to steer remote i2c i2c_mux:rem to two sets of
    16 INA219 ADCs. Note they are only on leg0 and leg1</doc>
    <params clobber_ok="" interface="2" drv="pca9546" slv="0x70"
    map="adc_mux"></params>
  </control>
"""

#         drvname,  slv,    name,          nom,   sense,  mux, is_calib
inas = [('ina219', '0x40', 'vs_wlan',      3.300, 0.100, 'rem', True),
        ('ina219', '0x41', 'vs',           0.975, 0.040, 'rem', True),
        ('ina219', '0x42', 'v_vddq',       1.200, 0.010, 'rem', True),
        ('ina219', '0x43', 'backlight',   12.300, 0.040, 'rem', True),
        ('ina219', '0x44', '3vs_emmc',     3.000, 0.040, 'rem', True),
        ('ina219', '0x45', '18vs_emmc',    1.800, 0.100, 'rem', True),
        ('ina219', '0x46', 'vs_audio_spk', 5.000, 0.040, 'rem', True),
        ('ina219', '0x47', 'vs_camera',    3.300, 0.100, 'rem', True),
        ('ina219', '0x48', 'vs_tp',        3.300, 0.100, 'rem', True),
        ('ina219', '0x49', 'apu_core',     0.850, 0.001, 'rem', True),
        ('ina219', '0x4a', 'apu_core_nb',  0.875, 0.001, 'rem', True),
        ('ina219', '0x4b', 'alw_ec',       3.300, 0.100, 'rem', True),
        ('ina219', '0x4c', 'vs_ssd',       3.300, 0.040, 'rem', True),
        ('ina219', '0x4d', 'v_batt',      12.300, 0.005, 'rem', True),
        ('ina219', '0x4e', 'vs_edp',       3.300, 0.010, 'rem', True),
        ('ina219', '0x4f', 'vs_fan',       5.000, 0.100, 'rem', True),
]
