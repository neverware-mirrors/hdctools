# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Ensure servo v4 manufacturing script is robust."""


import unittest

import mfg_servo_v4 as mfg

class TestMfgServoV4(unittest.TestCase):


  def setUp(self):
    """Set up serialname stubs."""
    unittest.TestCase.setUp(self)
    # G is one of the valid prefixes i.e. known manufacteurer.
    self.supplier = 'G'
    # A valid suffix is purely digits for example.
    self.suffix = '9999'
    # These three attributes are valid parts of the YYMMDD component.
    self.year = '19'
    self.month = '09'
    self.day = '17'

  def buildSerial(self):
    """Return serialname from components."""
    return self.supplier + self.year + self.month + self.day + self.suffix

  def test_SerialNumberRegexSupplierInvalid(self):
    """Ensure regex rejects unknown supplier."""
    self.supplier = 'Z'
    assert not mfg.RE_SERIALNO.match(self.buildSerial())

  def test_SerialNumberRegexDatesValid(self):
    """Ensure date-checking portion of regex WAI."""
    assert mfg.RE_SERIALNO.match(self.buildSerial())

  def test_SerialNumberRegexDatesInvalidDay(self):
    """Ensure date-checking portion of regex rejects invalid day."""
    # Check invalid day
    self.day = '00'
    assert not mfg.RE_SERIALNO.match(self.buildSerial())
    # Check non-existant 2-digit day.
    self.day = '32'
    assert not mfg.RE_SERIALNO.match(self.buildSerial())
    # Check ensure 3-digit day is rejected.
    self.day = '111'
    assert not mfg.RE_SERIALNO.match(self.buildSerial())

  def test_SerialNumberRegexDatesInvalidMonth(self):
    """Ensure date-checking portion of regex rejects invalid month."""
    # Check invalid month
    self.month = '00'
    assert not mfg.RE_SERIALNO.match(self.buildSerial())
    # Check non-existant 2-digit month.
    self.month = '13'
    assert not mfg.RE_SERIALNO.match(self.buildSerial())
    # Check ensure 3-digit month is rejected.
    self.month = '111'

if __name__ == '__main__':
  unittest.main()
