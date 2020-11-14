# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Module to manage servod-wide recovery mode status."""

# Module flag to report whether servod instance is in recovery mode.
RECOVERY_ACTIVE = False


def set_recovery_active():
  """Activate recovery mode on the instance."""
  global RECOVERY_ACTIVE
  RECOVERY_ACTIVE = True


def is_recovery_active():
  """Report whether recovery mode is active."""
  return RECOVERY_ACTIVE
