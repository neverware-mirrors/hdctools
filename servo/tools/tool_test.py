# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import tool


class TestTool(unittest.TestCase):

  def test_ConvertNameToMethodNoCamel(self):
    """Verify that strings without '-' only get capitalized."""
    name = 'hi'
    assert tool._ConvertNameToMethod(name) == 'Hi'

  def test_ConvertNameToMethodDoubleCamel(self):
    """Verify proper camel-case conversion for strings containing '-'."""
    name = 'hi-there-friends'
    assert tool._ConvertNameToMethod(name) == 'HiThereFriends'

if __name__ == '__main__':
  unittest.main()
