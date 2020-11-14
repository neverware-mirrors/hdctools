# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Software flag module to store and report binary status."""

import hw_driver


# pylint: disable=invalid-name
# This follows servod drv naming convention
class sflag(hw_driver.HwDriver):
  """A driver to store and report an on/off flag."""

  # This is a binary flag
  VALID_VALUES = [0, 1]

  # This is not a constant but at the class level so that
  # it can be shared between set and get.
  # We use a list to allow for sharing across as the class will not make it
  # an instance variable if we write into the lists' 0th element.
  vstore = [None]

  def set(self, value):
    """Set the value to |value|."""
    # While these controls _should_ be using a map so that the values
    # are converted to on/off, we still need to make sure.
    value = int(value)
    if value not in self.VALID_VALUES:
      raise hw_driver.HwDriverError('Invalid value: %d' %
                                    self.vstore[0])
    self.vstore[0] = value

  def get(self):
    """Return the |self.vstore| for this flag."""
    if self.vstore[0] is None:
      # Initialize with a 0 unless a default is provided
      self.vstore[0] = int(self._params.get('default_value', 0))
    if self.vstore[0] not in self.VALID_VALUES:
      # The default must have been invalid. This is because set() guards
      # against invalid values already - the only other source of values.
      raise hw_driver.HwDriverError('Invalid default: %d' %
                                    self.vstore[0])
    return self.vstore[0]
