# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to initialize keyboard handlers."""

# TODO(crbug.com/874707): This is a temporary solution until a more complete
# approach to interface handling and overwriting is implemented, at which point
# this code will be removed in favor of usb_keyboard and keyboard being
# interfaces.

import time

import hw_driver
import keyboard_handlers


# pylint: disable=invalid-name
# Follows error naming convention in servod.
class kbHandlerInitError(hw_driver.HwDriverError):
  """Error class for keyboard initialization issues."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class kbHandlerInit(hw_driver.HwDriver):
  """Class to handle initialization of different types of keyboard handlers."""
  # pylint: disable=protected-access
  # This class needs to set the private handlers inside Servod instance

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object; servod in this case.
      params: dictionary of params
        -handler_type(key) type of keyboard handler to use
    """
    super(kbHandlerInit, self).__init__(interface, params)
    self._servo = self._interface
    self._handler_type = self._params.get('handler_type', None)

  def _Get_init_usb_keyboard(self):
    """Return whether the usb keyboard on the servo instance is initialized."""
    if not self._servo._usb_keyboard:
      # Setup the keyboard handler and turn it off.
      self._servo.set('init_usb_keyboard', 'off')
    return int(self._servo._usb_keyboard.is_open())

  def _setup_usb_keyboard(self, value):
    """Setup the usb keyboard on the servo instance."""
    # Avoid reinitializing the same usb keyboard handler.
    if self._servo._usbkm232:
      usb_kb = keyboard_handlers.USBkm232Handler(self._servo,
                                                 self._servo_usbkm232)
    else:
      self._logger.debug('No device path specified for usbkm232 handler. Use '
                         'the servo atmega chip to handle.')
      # Use servo onboard keyboard emulator.
      if not self._servo._syscfg.is_control('atmega_rst'):
        msg = 'No atmega in servo board. So no keyboard support.'
        self._logger.warn(msg)
        raise kbHandlerInitError(msg)
      # This flag is used in servo v2/v3 to setup the atmega chip properly.
      legacy_atmega = 'init_atmega_uart' in self._params
      usb_kb = keyboard_handlers.ServoUSBkm232Handler(self._servo,
                                                      legacy_atmega)
    self._servo._usb_keyboard = usb_kb

  def _Set_init_usb_keyboard(self, value):
    if not self._servo._usb_keyboard:
      # Setup the keyboard always, and then turn on/off as needed.
      self._setup_usb_keyboard(value)
    if value:
      self._servo._usb_keyboard.open()
    else:
      self._servo._usb_keyboard.close()

  def _Get_init_default_keyboard(self):
    """Return whether the keyboard on the servo instance is initialized."""
    if not self._servo._keyboard:
      # Setup the keyboard handler and turn it off.
      self._servo.set('init_keyboard', 'off')
    return int(self._servo._keyboard.is_open())

  def _Set_init_default_keyboard(self, value):
    """Initialize the default keyboard on the servo instance."""
    if not self._servo._keyboard:
      if self._handler_type == 'usb':
        # Call through servo instead of calling method directly, because the
        # |_params| for default keyboard is not the same as for usb keyboard.
        if self._servo._syscfg.is_control('init_usb_keyboard'):
          self._servo.set('init_usb_keyboard', value)
          self._servo._keyboard = self._servo._usb_keyboard
        else:
          # This might be working as intended e.g. micro without a v4.
          # Warn the user about this, but don't make a scene.
          self._logger.warn('The servo setup does not have a usb keyboard '
                            'emulator. Will not throw an error, but note '
                            'that the keyboard controls will fail, as no '
                            'keyboard could be setup.')
      else:
        # The main keyboard is a normal keyboard handler.
        handler_class_name = '%sHandler' % self._handler_type
        handler_class = getattr(keyboard_handlers, handler_class_name)
        self._servo._keyboard = handler_class(self._servo)
    if value:
      self._servo._keyboard.open()
    else:
      # Here, we want to turn off the kb handler.
      self._servo._keyboard.close()
