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
        'handler' optional, indicate if default or usb keyboard handler should
                  be used for key press execution.
    """
    super(kb, self).__init__(interface, params.copy())
    # pylint: disable=protected-access
    handler = self._params.get('handler', 'default')
    if handler not in ['default', 'usb']:
      raise KbError('Unknown keyboard handler requested: %s' % handler)
    # As the user is intending to use the keyboard handler, initialize it
    # anyways.
    if handler == 'default':
      interface.set('init_keyboard', 'on')
    if handler == 'usb':
      interface.set('init_usb_keyboard', 'on')
    self._key = params['key']

  def _Set_key(self, duration):
    """Press key combo for |duration| seconds.

    Note: the key to press is defined in the params of the control under
    'key'.

    Args:
      duration: seconds to hold the key pressed.

    Raises:
      KbError: if key is not a member of kb_precanned map.
    """
    keyboard = self._interface._keyboard
    if  self._params.get('handler', 'default') == 'usb':
      keyboard = self._interface._usb_keyboard
    if not keyboard:
      raise KbError('Keyboard handler not setup.')
    try:
      func = getattr(keyboard, self._key)
    except AttributeError:
      raise KbError('Key %s not found.' % self._key)
    func(press_secs=duration)

  def _Set_arb_key_config(self, key):
    """Set the key to be pressed when arb_key control is called

    Args:
      key: the key to press when arb_key is called
    """
    self._keyboard.arb_key_config(key)
