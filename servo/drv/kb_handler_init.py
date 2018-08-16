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
import servo.keyboard_handlers


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
    return self._servo._usb_keyboard != None

  def _Set_init_usb_keyboard(self, value):
    """Initialize the usb keyboard on the servo instance."""
    # Avoid reinitializing the same usb keyboard handler.
    if value and not self._servo._usb_keyboard:
      if self._servo._usbkm232 is None:
        self._logger.info('No device path specified for usbkm232 handler. Use '
                          'the servo atmega chip to handle.')

        # Use servo onboard keyboard emulator.
        if not self._servo._syscfg.is_control('atmega_rst'):
          self._logger.warn('No atmega in servo board. So no keyboard support.')
          self._servo._usb_keyboard = None
          return

        self._servo.set('atmega_rst', 'on')
        self._servo.set('at_hwb', 'off')
        self._servo.set('atmega_rst', 'off')
        self._servo._usbkm232 = self._servo.get('atmega_pty')

        # We don't need to set the atmega uart settings if we're a servo v4.
        if 'init_atmega_uart' in self._params:
          self._servo.set('atmega_baudrate', '9600')
          self._servo.set('atmega_bits', 'eight')
          self._servo.set('atmega_parity', 'none')
          self._servo.set('atmega_sbits', 'one')
          self._servo.set('usb_mux_sel4', 'on')
          self._servo.set('usb_mux_oe4', 'on')
          # Allow atmega bootup time.
          time.sleep(1.0)

      self._logger.info('USBKM232: %s', self._servo._usbkm232)
      usb_kb =  servo.keyboard_handlers.USBkm232Handler(self._servo,
                                                        self._servo._usbkm232)
      self._servo._usb_keyboard = usb_kb

  def _Get_init_default_keyboard(self):
    """Return whether the keyboard on the servo instance is initialized."""
    return self._servo._keyboard != None

  def _Set_init_default_keyboard(self, value):
    """Initialize the default keyboard on the servo instance."""
    if value:
      if self._handler_type == 'usb':
        # Call through servo instead of calling method directly, because the
        # |_params| for default keyboard is not the same as for usb keyboard.
        self._servo.set('init_usb_keyboard', value)
        self._servo._keyboard = self._servo._usb_keyboard
      else:
        # The main keyboard is a normal keyboard handler.
        handler_class_name = '%sHandler' % self._handler_type
        handler_class = getattr(servo.keyboard_handlers, handler_class_name)
        self._servo._keyboard = handler_class(self._servo)
