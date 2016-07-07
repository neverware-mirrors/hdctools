# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [
        # TODO(nsanders): Come up with a way to support multiple voltages.
        (0x40, 'ppdut5', 5.0, 0.005, 'rem', True),
        (0x41, 'ppchg5', 5.0, 0.005, 'rem', True),
       ]
# Must be servo v4's i2c interface array index + 1 from servo_interface.py.
interface = 23
