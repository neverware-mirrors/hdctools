# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Collection of available tools in the system."""

import device
import instance

REGISTERED_TOOLS = [
    device.Device,
    instance.Instance
]
