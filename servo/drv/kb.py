# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for keyboard control servo feature."""

import hw_driver


class KbError(Exception):
  """Error class for kb class."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class kb(hw_driver.HwDriver):
  """HwDriver wrapper around servod's keyboard functions."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object; servod in this case.
      params: dictionary of params;
        'key' attribute indicates what key should be pressed with each instance.
    """
    super(kb, self).__init__(interface, params.copy())
    # pylint: disable=protected-access
    self._keyboard = interface._keyboard
    self._key = params['key']

  def set(self, duration):
    """Press key combo for |duration| seconds.

    Note: the key to press is defined in the params of the control under
    'key'.

    Args:
      duration: seconds to hold the key pressed.

    Raises:
      KbError: if key is not a member of kb_precanned map.
    """
    try:
      func = getattr(self._keyboard, self._key)
    except AttributeError:
      raise KbError('Key %s not found' % self._key)
    func(press_secs=duration)
