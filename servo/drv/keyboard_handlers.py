# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Expects to be run in an environment with sudo and no interactive password
# prompt, such as within the Chromium OS development chroot.
from __future__ import print_function

import logging
import os
import time

from hw_driver import HwDriverError
import serial


class _HandlerTemplate(object):
  """Template for all handlers to support common open/close operations."""

  def __init__(self):
    # The base subclasses need to handle opening themselves up.
    self._logger = logging.getLogger(type(self).__name__)
    self._open = False

  def is_open(self):
    """Query whether keyboard handler is open for use."""
    return self._open

  def open(self):
    """Open the keyboard handler for use."""
    self._open = True

  def close(self):
    """Close the keyboard handler for use."""
    self._open = False


class NoopHandler(_HandlerTemplate):
  """Noop keyboard handler that always keeps the keyboard closed.

  For some use-cases a proper keyboard handler cannot be initialized e.g.
  missing hardware. If those cases are not necessarily blocking, use a
  NoopHandler. It will warn every time open/close are being used that
  they are noops, but will not issue an exception.

  As open open() and close() just print warnings, |self._open| stays False
  and is_open() always returns False
  """

  _BASE_WRN = ('Using a noop keyboard handler. Check logs to see why it is '
               'in use and address issue if full keyboard functionality is '
               'needed.')

  def open(self):
    """Print warning only."""
    self._logger.warn(self._BASE_WRN)

  def close(self):
    """Print warning only."""
    self._logger.warn(self._BASE_WRN)


class _BaseHandler(_HandlerTemplate):
  """Base class for keyboard handlers.
    """
  # Power button press delays in seconds.
  #
  # The EC specification says that 8.0 seconds should be enough
  # for the long power press.  However, some platforms need a bit
  # more time.  Empirical testing has found these requirements:
  #   Alex: 8.2 seconds
  #   ZGB:  8.5 seconds
  # The actual value is set to the largest known necessary value.
  #
  # TODO(jrbarnette) Being generous is the right thing to do for
  # existing platforms, but if this code is to be used for
  # qualification of new hardware, we should be less generous.
  LONG_DELAY = 8.5
  SHORT_DELAY = 0.2
  NORMAL_TRANSITION_DELAY = 1.2

  # Maximum number of times to re-read power button on release.
  RELEASE_RETRY_MAX = 5

  # Default minimum time interval between 'press' and 'release'
  # keyboard events.
  SERVO_KEY_PRESS_DELAY = 0.1

  KEY_MATRIX = None

  def __init__(self, servo):
    """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
    super(_BaseHandler, self).__init__()
    # TODO(fdeng): crbug.com/298379
    # We should move servo object out of servo object
    # to minimize the dependencies on the rest of Autotest.
    self._servo = servo
    board = self._servo.get_board()

  def power_long_press(self):
    """Simulate a long power button press."""
    # After a long power press, the EC may ignore the next power
    # button press (at least on Alex).  To guarantee that this
    # won't happen, we need to allow the EC one second to
    # collect itself.
    # TODO(waihong): Make this delay as one of board specific configs.
    self.power_key(self.LONG_DELAY)
    time.sleep(1.0)

  def power_normal_press(self):
    """Simulate a normal power button press."""
    self.power_key()

  def power_short_press(self):
    """Simulate a short power button press."""
    self.power_key(self.SHORT_DELAY)

  def power_key(self, press_secs=''):
    """Simulate a power button press.

        Args:
          press_secs: Time in seconds to simulate the keypress.
        """
    if press_secs is '':
      press_secs = self.NORMAL_TRANSITION_DELAY

    # Check if pwr_button control available, by setting it to
    # its current value. Use pwr_button control by default.
    # Otherwise, use pwr_button_hold which calls a single EC
    # console command to toggle power button, for the CCD case.
    servo_type = self._servo.get('servo_type')
    is_ccd = 'ccd' in servo_type and 'servo_micro' not in servo_type

    if is_ccd:
      use_hold_command = True
    else:
      try:
        value = self._servo.get('pwr_button')
        self._servo.set('pwr_button', value)
        use_hold_command = False
      except HwDriverError:
        use_hold_command = True

    if use_hold_command:
      self.power_key_hold(press_secs)
    else:
      self.power_key_press_release(press_secs)

  def power_key_hold(self, press_secs):
    """Simulate a power button by a single EC console command.

        Args:
          press_secs: Time in seconds to simulate the keypress.
        """
    # Convert to milliseconds
    self._servo.set('pwr_button_hold', int(press_secs * 1000))

  def power_key_press_release(self, press_secs):
    """Simulate a power button by setting it to press and then release.

        Args:
          press_secs: Time in seconds to simulate the keypress.
        """
    self._logger.info('Pressing power button for %.4f secs', press_secs)
    self._servo.set_get_all(
        ['pwr_button:press',
         'sleep:%.4f' % press_secs, 'pwr_button:release'])
    # TODO(tbroch) Different systems have different release times on the
    # power button that this loop addresses.  Longer term we may want to
    # make this delay platform specific.
    retry = 1
    while True:
      value = self._servo.get('pwr_button')
      if value == 'release' or retry > self.RELEASE_RETRY_MAX:
        break
      self._logger.info('Waiting for pwr_button to release, retry %d.', retry)
      retry += 1
      time.sleep(self.SHORT_DELAY)

  def ctrl_d(self, press_secs=''):
    """Simulate Ctrl-d simultaneous button presses."""
    NotImplementedError()

  def ctrl_u(self, press_secs=''):
    """Simulate Ctrl-u simultaneous button presses."""
    NotImplementedError()

  def ctrl_s(self, press_secs=''):
    """Simulate Ctrl-s simultaneous button presses."""
    NotImplementedError()

  def ctrl_enter(self, press_secs=''):
    """Simulate Ctrl-enter simultaneous button presses."""
    NotImplementedError()

  def ctrl_key(self, press_secs=''):
    """Simulate Enter key button press."""
    NotImplementedError()

  def arrow_up(self, press_secs=''):
    """Simulate ArrowUp key button press."""
    NotImplementedError()

  def arrow_down(self, press_secs=''):
    """Simulate ArrowDown key button press."""
    NotImplementedError()

  def enter_key(self, press_secs=''):
    """Simulate Enter key button press."""
    NotImplementedError()

  def refresh_key(self, press_secs=''):
    """Simulate Refresh key (F3) button press."""
    NotImplementedError()

  def ctrl_refresh_key(self, press_secs=''):
    """Simulate Ctrl and Refresh (F3) simultaneous press.

        This key combination is an alternative of Space key.
        """
    NotImplementedError()

  def imaginary_key(self, press_secs=''):
    """Simulate imaginary key button press.

        Maps to a key that doesn't physically exist.
        """
    NotImplementedError()

  def sysrq_x(self, press_secs=''):
    """Simulate Alt VolumeUp X simultaneous press.

        This key combination is the kernel system request (sysrq) X.
        """
    NotImplementedError()

  def arb_key(self, press_secs=''):
    """Simulate an arbitrary key press.
        """
    NotImplementedError()

  def arb_key_config(self, key):
    """Set key for an arbitrary key press.
        """
    self._arb_key = key

class MatrixKeyboardHandler(_BaseHandler):
  """Matrix keyboard handler for DUT with internal keyboards.

    It works on mostly all devices, with or without Chrome EC.
    """
  KEY_MATRIX = {
      'ctrl_refresh': ['0', '0', '0', '1'],
      'ctrl_d': ['0', '1', '0', '0'],
      'd': ['0', '1', '1', '1'],
      'ctrl_enter': ['1', '0', '0', '0'],
      'enter': ['1', '0', '1', '1'],
      'ctrl': ['1', '1', '0', '0'],
      'refresh': ['1', '1', '0', '1'],
      'unused': ['1', '1', '1', '0'],
      'none': ['1', '1', '1', '1']
  }

  def __init__(self, servo):
    """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
    super(MatrixKeyboardHandler, self).__init__(servo)
    self.open()

  def _press_keys(self, key):
    """Simulate button presses.

        Note, key presses will remain on indefinitely. See
            _press_and_release_keys for release procedure.
        """
    (m1_a1, m1_a0, m2_a1, m2_a0) = self.KEY_MATRIX[key]
    self._servo.set_get_all([
        'kbd_m2_a0:%s' % m2_a0,
        'kbd_m2_a1:%s' % m2_a1,
        'kbd_m1_a0:%s' % m1_a0,
        'kbd_m1_a1:%s' % m1_a1, 'kbd_en:on'
    ])

  def _press_and_release_keys(self, key, press_secs=''):
    """Simulate button presses and release."""
    if press_secs is '':
      press_secs = self.SERVO_KEY_PRESS_DELAY
    self._press_keys(key)
    time.sleep(press_secs)
    self._servo.set('kbd_en', 'off')

  def ctrl_d(self, press_secs=''):
    """Simulate Ctrl-d simultaneous button presses."""
    self._press_and_release_keys('ctrl_d', press_secs)

  def ctrl_enter(self, press_secs=''):
    """Simulate Ctrl-enter simultaneous button presses."""
    self._press_and_release_keys('ctrl_enter', press_secs)

  def ctrl_key(self, press_secs=''):
    """Simulate Enter key button press."""
    self._press_and_release_keys('ctrl', press_secs)

  def enter_key(self, press_secs=''):
    """Simulate Enter key button press."""
    self._press_and_release_keys('enter', press_secs)

  def refresh_key(self, press_secs=''):
    """Simulate Refresh key (F3) button press."""
    self._press_and_release_keys('refresh', press_secs)

  def ctrl_refresh_key(self, press_secs=''):
    """Simulate Ctrl and Refresh (F3) simultaneous press.

        This key combination is an alternative of Space key.
        """
    self._press_and_release_keys('ctrl_refresh', press_secs)

  def imaginary_key(self, press_secs=''):
    """Simulate imaginary key button press.

        Maps to a key that doesn't physically exist.
        """
    self._press_and_release_keys('unused', press_secs)


class StoutHandler(MatrixKeyboardHandler):
  """Stout keyboard handler for DUT with internal keyboards.

    """

  KEY_MATRIX = {
      'ctrl_d': ['0', '0', '0', '1'],
      'd': ['0', '0', '1', '1'],
      'unused': ['0', '1', '1', '1'],
      'rec_mode': ['1', '0', '0', '0'],
      'ctrl_enter': ['1', '0', '0', '1'],
      'enter': ['1', '0', '1', '1'],
      'ctrl': ['1', '1', '0', '1'],
      'refresh': ['1', '1', '1', '0'],
      'ctrl_refresh': ['1', '1', '1', '1'],
      'none': ['1', '1', '1', '1']
  }

  def __init__(self, servo):
    """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
    super(StoutHandler, self).__init__(servo)
    self.open()


class ParrotHandler(MatrixKeyboardHandler):
  """Parrot keyboard handler for DUT with internal keyboards.

    """

  KEY_MATRIX = {
      'ctrl_d': ['0', '0', '1', '0'],
      'd': ['0', '0', '1', '1'],
      'ctrl_enter': ['0', '1', '1', '0'],
      'enter': ['0', '1', '1', '1'],
      'ctrl_refresh': ['1', '0', '0', '1'],
      'unused': ['1', '1', '0', '0'],
      'refresh': ['1', '1', '0', '1'],
      'ctrl': ['1', '1', '1', '0'],
      'none': ['1', '1', '1', '1']
  }

  def __init__(self, servo):
    """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
    super(ParrotHandler, self).__init__(servo)
    self.open()

class ChromeECHandler(_BaseHandler):
  """Chrome EC keyboard handler for DUT with Chrome EC.
    """

  # en-US key matrix (from "kb membrane pin matrix.pdf")
  KEY_MATRIX = {
      # key: (row, col)
      '`': (3, 1),
      '1': (6, 1),
      '2': (6, 4),
      '3': (6, 2),
      '4': (6, 3),
      '5': (3, 3),
      '6': (3, 6),
      '7': (6, 6),
      '8': (6, 5),
      '9': (6, 9),
      '0': (6, 8),
      '-': (3, 8),
      '=': (0, 8),
      'q': (7, 1),
      'w': (7, 4),
      'e': (7, 2),
      'r': (7, 3),
      't': (2, 3),
      'y': (2, 6),
      'u': (7, 6),
      'i': (7, 5),
      'o': (7, 9),
      'p': (7, 8),
      '[': (2, 8),
      ']': (2, 5),
      '\\': (3, 11),
      'a': (4, 1),
      's': (4, 4),
      'd': (4, 2),
      'f': (4, 3),
      'g': (1, 3),
      'h': (1, 6),
      'j': (4, 6),
      'k': (4, 5),
      'l': (4, 9),
      ';': (4, 8),
      '\'': (1, 8),
      'z': (5, 1),
      'x': (5, 4),
      'c': (5, 2),
      'v': (5, 3),
      'b': (0, 3),
      'n': (0, 6),
      'm': (5, 6),
      ',': (5, 5),
      '.': (5, 9),
      '/': (5, 8),
      ' ': (5, 11),
      '<right>': (6, 12),
      '<alt_r>': (0, 10),
      '<down>': (6, 11),
      '<tab>': (2, 1),
      '<f10>': (0, 4),
      '<shift_r>': (7, 7),
      '<ctrl_r>': (4, 0),
      '<esc>': (1, 1),
      '<backspace>': (1, 11),
      '<f2>': (3, 2),
      '<alt_l>': (6, 10),
      '<ctrl_l>': (2, 0),
      '<f1>': (0, 2),
      '<search>': (0, 1),
      '<f3>': (2, 2),
      '<f4>': (1, 2),
      '<f5>': (3, 4),
      '<f6>': (2, 4),
      '<f7>': (1, 4),
      '<f8>': (2, 9),
      '<f9>': (1, 9),
      '<up>': (7, 11),
      '<shift_l>': (5, 7),
      '<enter>': (4, 11),
      '<left>': (7, 12)
  }

  def __init__(self, servo):
    """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
    super(ChromeECHandler, self).__init__(servo)
    base_board = self._servo.get_base_board()
    if base_board:
      self._ec_uart_regexp = base_board + '_ec_uart_regexp'
      self._ec_uart_cmd = base_board + '_ec_uart_cmd'
    else:
      self._ec_uart_regexp = 'ec_uart_regexp'
      self._ec_uart_cmd = 'ec_uart_cmd'
    self.open()

  def _send_command(self, command):
    """Send command through UART.

        This function opens UART pty when called, and then command is sent
        through UART.

        @param command: The command to send.
        """
    self._servo.set(self._ec_uart_regexp, 'None')
    self._servo.set(self._ec_uart_cmd, command)

  def _press_and_release_keys(self, keys, press_secs=''):
    """Simulate a key combination press and release.

        The key combination (multiple keys) are all pressed and then
        all released.

        @param keys: A list of key names, which are the keys of KEY_MATRIX.
        """
    if press_secs is '':
      press_secs = self.SERVO_KEY_PRESS_DELAY
    for key in keys:
      # Send EC command: kbpress col row pressed
      self._send_command('kbpress %d %d 1' % (self.KEY_MATRIX[key][1],
                                              self.KEY_MATRIX[key][0]))
    time.sleep(press_secs)
    for key in keys:
      # Send EC command: kbpress col row pressed
      self._send_command('kbpress %d %d 0' % (self.KEY_MATRIX[key][1],
                                              self.KEY_MATRIX[key][0]))

  def ctrl_d(self, press_secs=''):
    """Simulate Ctrl-d simultaneous button presses."""
    self._press_and_release_keys(['<ctrl_l>', 'd'], press_secs)

  def ctrl_u(self, press_secs=''):
    """Simulate Ctrl-u simultaneous button presses."""
    self._press_and_release_keys(['<ctrl_l>', 'u'], press_secs)

  def ctrl_s(self, press_secs=''):
    """Simulate Ctrl-s simultaneous button presses."""
    self._press_and_release_keys(['<ctrl_l>', 's'], press_secs)

  def ctrl_enter(self, press_secs=''):
    """Simulate Ctrl-enter simultaneous button presses."""
    self._press_and_release_keys(['<enter>'], press_secs)

  def ctrl_key(self, press_secs=''):
    """Simulate Enter key button press."""
    self._press_and_release_keys(['<ctrl_l>'], press_secs)

  def arrow_up(self, press_secs=''):
    """Simulate ArrowUp key button press."""
    self._press_and_release_keys(['<up>'], press_secs)

  def arrow_down(self, press_secs=''):
    """Simulate ArrowDown key button press."""
    self._press_and_release_keys(['<down>'], press_secs)

  def enter_key(self, press_secs=''):
    """Simulate Enter key button press."""
    self._press_and_release_keys(['<enter>'], press_secs)

  def refresh_key(self, press_secs=''):
    """Simulate Refresh key (F3) button press."""
    self._press_and_release_keys(['<f3>'], press_secs)

  def ctrl_refresh_key(self, press_secs=''):
    """Simulate Ctrl and Refresh (F3) simultaneous press.

        This key combination is an alternative of Space key.
        """
    self._press_and_release_keys(['<ctrl_l>', '<f3>'], press_secs)

  def sysrq_x(self, press_secs=''):
    """Simulate Alt VolumeUp X simultaneous press.

        This key combination is the kernel system request (sysrq) x.
        """
    self._press_and_release_keys(['<alt_l>', '<f10>', 'x'], press_secs)

  def arb_key(self, press_secs=''):
    """Simulate an arbitrary key press."""
    self._press_and_release_keys([self._arb_key], press_secs)


class USBkm232Handler(_BaseHandler):
  """Keyboard handler for devices without internal keyboard."""

  MAX_RSP_RETRIES = 10
  USB_QUEUE_DEPTH = 6
  CLEAR = '\x38'
  KEYS = {
      #row 1
      '`': 1,
      '1': 2,
      '2': 3,
      '3': 4,
      '4': 5,
      '5': 6,
      '6': 7,
      '7': 8,
      '8': 9,
      '9': 10,
      '0': 11,
      '-': 12,
      '=': 13,
      '<undef1>': 14,
      '<backspace>': 15,
      '<tab>': 16,
      'q': 17,
      'w': 18,
      'e': 19,
      'r': 20,
      't': 21,
      'y': 22,
      'u': 23,
      'i': 24,
      'o': 25,
      'p': 26,
      '[': 27,
      ']': 28,
      '\\': 29,
      # row 2
      '<capslock>': 30,
      'a': 31,
      's': 32,
      'd': 33,
      'f': 34,
      'g': 35,
      'h': 36,
      'j': 37,
      'k': 38,
      'l': 39,
      ';': 40,
      '\'': 41,
      '<undef2>': 42,
      '<enter>': 43,
      # row 3
      '<lshift>': 44,
      '<undef3>': 45,
      'z': 46,
      'x': 47,
      'c': 48,
      'v': 49,
      'b': 50,
      'n': 51,
      'm': 52,
      ',': 53,
      '.': 54,
      '/': 55,
      '[clear]': 56,
      '<rshift>': 57,
      # row 4
      '<lctrl>': 58,
      '<undef5>': 59,
      '<lalt>': 60,
      ' ': 61,
      '<ralt>': 62,
      '<undef6>': 63,
      '<rctrl>': 64,
      '<undef7>': 65,
      '<mouse_left>': 66,
      '<mouse_right>': 67,
      '<mouse_up>': 68,
      '<mouse_down>': 69,
      '<lwin>': 70,
      '<rwin>': 71,
      '<win apl>': 72,
      '<mouse_lbtn_press>': 73,
      '<mouse_rbtn_press>': 74,
      '<insert>': 75,
      '<delete>': 76,
      '<mouse_mbtn_press>': 77,
      '<undef16>': 78,
      '<larrow>': 79,
      '<home>': 80,
      '<end>': 81,
      '<undef23>': 82,
      '<uparrow>': 83,
      '<downarrow>': 84,
      '<pgup>': 85,
      '<pgdown>': 86,
      '<mouse_scr_up>': 87,
      '<mouse_scr_down>': 88,
      '<rarrow>': 89,
      # numpad
      '<numlock>': 90,
      '<num7>': 91,
      '<num4>': 92,
      '<num1>': 93,
      '<undef27>': 94,
      '<num/>': 95,
      '<num8>': 96,
      '<num5>': 97,
      '<num2>': 98,
      '<num0>': 99,
      '<num*>': 100,
      '<num9>': 101,
      '<num6>': 102,
      '<num3>': 103,
      '<num.>': 104,
      '<num->': 105,
      '<num+>': 106,
      '<numenter>': 107,
      '<undef28>': 108,
      '<mouse_slow>': 109,
      # row 0
      '<esc>': 110,
      '<mouse_fast>': 111,
      '<f1>': 112,
      '<f2>': 113,
      '<f3>': 114,
      '<f4>': 115,
      '<f5>': 116,
      '<f6>': 117,
      '<f7>': 118,
      '<f8>': 119,
      '<f9>': 120,
      '<f10>': 121,
      '<f11>': 122,
      '<f12>': 123,
      '<prtscr>': 124,
      '<scrllk>': 125,
      '<pause/brk>': 126,
  }

  def __init__(self, servo, serial_device):
    """Constructor for usbkm232 class."""
    super(USBkm232Handler, self).__init__(servo)
    if serial_device is None:
      raise Exception('No device specified when '
                      'initializing usbkm232 keyboard handler')
    self.serial_device = serial_device
    self.serial = None
    self.open()
    self._logger.info('USBKM232: %s', self.serial_device)

  def open(self):
    """Open serial connection to serial_device."""
    if self.is_open():
      return
    self.serial = serial.Serial(self.serial_device, 9600, timeout=0.1)
    self.serial.interCharTimeout = 0.5
    self.serial.timeout = 0.5
    self.serial.writeTimeout = 0.5
    super(USBkm232Handler, self).open()

  def close(self):
    """Close usbkm232 device, and assert rst on atmega if necessary."""
    if not self.is_open():
      return
    self.serial.close()
    super(USBkm232Handler, self).close()

  def _test_atmega(self):
    """Send and receive a key from the atmega to verify it is present.

       Returns:
         Raises exception if no correct response is received.
       """
    self.serial.write(chr(0))
    rsp = self.serial.read(1)
    if not rsp or (ord(rsp) != 0xff):
      self._logger.error('Presence check response from atmega KB emu: rsp: %s',
                         rsp)
      self._logger.error('Atmega KB offline: failed to communicate.')

  def _press(self, press_ch):
    """Encode and return character to press using usbkm232.

        Args:
          press_ch: character to press

        Returns:
          Proper encoding to send to the uart side of the usbkm232 to create the
          desired key press.
        """
    return '%c' % self.KEYS[press_ch]

  def _release(self, release_ch):
    """Encode and return character to release using usbkm232.

        This value is simply the _press_ value + 128

        Args:
          release_ch: character to release

        Returns:
          Proper encoding to send to the uart side of the usbkm232 to create the
          desired key release.
        """
    return '%c' % (self.KEYS[release_ch] | 0x80)

  def _rsp(self, orig_ch):
    """Check response after sending character to usbkm232.

        The response is the one's complement of the value sent.  This method
        blocks until proper response is received.

        Args:
          orig_ch: original character sent.

        Raises:
          Exception: if response was incorrect or timed out
        """
    count = 0
    rsp = self.serial.read(1)
    while (len(rsp) != 1 or ord(orig_ch) != (~ord(rsp) & 0xff)) \
            and count < self.MAX_RSP_RETRIES:
      rsp = self.serial.read(1)
      print('re-read rsp')
      count += 1

    if count == self.MAX_RSP_RETRIES:
      raise Exception('Failed to get correct response from usbkm232')
    print('usbkm232: response [-] = \\0%03o 0x%02x' % (ord(rsp), ord(rsp)))

  def _write(self, mylist, check=False, clear=True):
    """Write list of commands to usbkm232.

        Args:
          mylist: list of encoded commands to send to the uart side of the
            usbkm232
          check: boolean determines whether response from usbkm232 should be
            checked.
          clear: boolean determines whether keytroke clear should be sent at end
            of the sequence.
        """
    # TODO(tbroch): USB queue depth is 6 might be more efficient to write
    #               more than just one make/break
    for i, write_ch in enumerate(mylist):
      print('usbkm232: writing  [%d] = \\0%03o 0x%02x' % \
            (i, ord(write_ch), ord(write_ch)))
      self.serial.write(write_ch)
      if check:
        self._rsp(write_ch)
      time.sleep(.05)

    if clear:
      print('usbkm232: clearing keystrokes')
      self.serial.write(self.CLEAR)
      if check:
        self._rsp(self.CLEAR)

  def writestr(self, mystr):
    """Write string to usbkm232.

        Args:
          mystr: string to send across the usbkm232
          """
    rlist = []
    for write_ch in mystr:
      rlist.append(self._press(write_ch))
      rlist.append(self._release(write_ch))
    self._write(rlist)

  def ctrl_d(self, press_secs=''):
    """Press and release ctrl-d sequence."""
    self._write([self._press('<lctrl>'), self._press('d')])

  def ctrl_u(self, press_secs=''):
    """Press and release ctrl-u sequence."""
    self._write([self._press('<lctrl>'), self._press('u')])

  def ctrl_s(self, press_secs=''):
    """Press and release ctrl-s sequence."""
    self._write([self._press('<lctrl>'), self._press('s')])

  def arrow_up(self, press_secs=''):
    """Press and release ArrowUp key."""
    self._write([self._press('<uparrow>')])

  def arrow_down(self, press_secs=''):
    """Press and release ArrowDown key."""
    self._write([self._press('<downarrow>')])

  def enter_key(self, press_secs=''):
    """Press and release enter"""
    self._write([self._press('<enter>')])

  def ctrl_key(self, press_secs=''):
    """Simulate Enter key button press."""
    self._write([self._press('<lctrl>')])

  def crtl_enter(self):
    """Press and release ctrl+enter"""
    self._write([self._press('<lctrl>'), self._press('<enter>')])

  def space_key(self):
    """Press and release space key."""
    self._write([self._press(' ')])

  def refresh_key(self, press_secs=''):
    """Simulate Refresh key (F3) button press."""
    self._write([self._press('<f3>')])

  def ctrl_refresh_key(self, press_secs=''):
    """Simulate Ctrl and Refresh (F3) simultaneous press.
        This key combination is an alternative of Space key.
        """
    self._write([self._press('<lctrl>'), self._press('<f3>')])

  def sysrq_x(self, press_secs=''):
    """Simulate Alt VolumeUp X simultaneous press.

        This key combination is the kernel system request (sysrq) x.
        """
    self._write([self._press('<lalt>'), self._press('<f10>'), self._press('x')])

  def arb_key(self, press_secs=''):
    """Simulate an arbitrary key press."""
    self._write([self._press(self._arb_key)])

  def tab(self):
    """Press and release tab"""
    self._write([self._press('<tab>')])

class ServoUSBkm232Handler(USBkm232Handler):
  """Keyboard handler for devices without internal keyboard."""


  def __init__(self, servo, legacy):
    """
    Args:
      servo: Servo device used to execute controls
      legacy: bool, true for servo v2, v3 as they require more setup.
    """
    servo.set('atmega_rst', 'on')
    servo.set('at_hwb', 'off')
    servo.set('atmega_rst', 'off')
    serial = servo.get('atmega_pty')
    self.legacy = legacy
    super(ServoUSBkm232Handler, self).__init__(servo, serial)

  def open(self):
    """Take atmega out of reset, and potentially do legacy setup."""
    if self.is_open():
      return
    # Ensure that the atmega is not in reset
    self._servo.set('atmega_rst', 'off')
    # Do proper setup for legacy devices
    if self.legacy:
      self._servo.set('atmega_baudrate', '9600')
      self._servo.set('atmega_bits', 'eight')
      self._servo.set('atmega_parity', 'none')
      self._servo.set('atmega_sbits', 'one')
      self._servo.set('usb_mux_sel4', 'on')
      self._servo.set('usb_mux_oe4', 'on')
    # Give the board enough time to boot up.
    time.sleep(1)
    super(ServoUSBkm232Handler, self).open()
    self._test_atmega()

  def close(self):
    """Set the atmega to reset before closing the serial port."""
    if not self.is_open():
      return
    # If using the atmega, ensure that the atmega is in reset.
    self._servo.set('atmega_rst', 'on')
    super(ServoUSBkm232Handler, self).close()
