# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines the interfaces for the different servo models."""

import collections

INTERFACE_DEFAULTS = collections.defaultdict(dict)

SERVO_ID_DEFAULTS = [(0x0403, 0x6011), (0x0403, 0x6014), (0x18d1, 0x5001),
                     (0x18d1, 0x5002), (0x18d1, 0x5004), (0x18d1, 0x500f),
                     (0x18d1, 0x5014), (0x18d1, 0x501a), (0x18d1, 0x501b)]

# servo v1 w/o FT4232h EEPROM programmed
INTERFACE_DEFAULTS[0x0403][0x6011] = \
  ['dummy',
   'ftdi_gpio',
   'ftdi_i2c',
   'ftdi_gpio',
   'ftdi_gpio',
  ]

# servo v1
INTERFACE_DEFAULTS[0x18d1][0x5001] = \
  ['dummy',
   'ftdi_gpio',
   'ftdi_i2c',
   'ftdi_gpio',
   'ftdi_gpio',
  ]

# servo V2
# Dummy interface 1 == JTAG via openocd
# Dummy interface 5,6 == SPI via flashrom
# ec3po_uart interface 9,10 == usbpd console, ec console. Applicable to servo v3
# as well.
SERVO_V2_DEFAULTS = [(0x18d1, 0x5002)]
for vid, pid in SERVO_V2_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     'ftdi_dummy',                      # 1
     'ftdi_i2c',                        # 2
     'ftdi_uart',                       # 3: uart3/legacy
     'ftdi_uart',                       # 4: ATMEGA
     'ftdi_dummy',                      # 5
     'ftdi_dummy',                      # 6
     'ftdi_uart',                       # 7: EC
     'ftdi_uart',                       # 8: AP
     {'name': 'ec3po_uart',             # 9: EC3PO(USBPD)
      'raw_pty': 'raw_usbpd_uart_pty'},
     {'name': 'ec3po_uart',             #10: EC3PO(EC)
      'raw_pty': 'raw_ec_uart_pty'},
    ]

# servo v3
SERVO_V3_DEFAULTS = [(0x18d1, 0x5004)]
for vid, pid in SERVO_V3_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     'bb_gpio',                          # 1
     {'name': 'dev_i2c', 'bus_num': 1},  # 2
     {'name': 'bb_uart', 'uart_num': 5,  # 3: uart3/legacy
      'txd': ['lcd_data8', 0x4],
      'rxd': ['lcd_data9', 0x4]},
     {'name': 'bb_uart', 'uart_num': 4}, # 4: ATMEGA
     'bb_adc',                           # 5
     {'name': 'dev_i2c', 'bus_num': 2},  # 6
     {'name': 'bb_uart', 'uart_num': 1}, # 7: EC
     {'name': 'bb_uart', 'uart_num': 2}, # 8: AP
     'dummy',                            # 9
     {'name': 'ec3po_uart',              #10: EC3PO(EC)
      'raw_pty': 'raw_ec_uart_pty'},
    ]

INTERFACE_DEFAULTS[0x0403][0x6014] = INTERFACE_DEFAULTS[0x18d1][0x5004]

# Ryu Raiden CCD
RAIDEN_DEFAULTS = [(0x18d1, 0x500f)]
for vid, pid in RAIDEN_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     {'name': 'stm32_uart', 'interface': 0}, # 1: EC_PD
     {'name': 'stm32_uart', 'interface': 1}, # 2: AP
     'dummy',                                # 3
     'dummy',                                # 4
     'dummy',                                # 5
     'dummy',                                # 6
     'dummy',                                # 7
     'dummy',                                # 8
     'dummy',                                # 9
     {'name': 'ec3po_uart',                  #10: dut ec console
      'raw_pty': 'raw_ec_uart_pty'},
    ]

# cr50 CCD
CCD_DEFAULTS = [(0x18d1, 0x5014)]
for vid, pid in CCD_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     {'name': 'stm32_uart', 'interface': 0}, # 1: Cr50 console
     {'name': 'stm32_i2c', 'interface': 5},  # 2: i2c
     'dummy',                                # 3
     'dummy',                                # 4
     'dummy',                                # 5
     'dummy',                                # 6
     {'name': 'stm32_uart', 'interface': 2}, # 7: EC/PD
     {'name': 'stm32_uart', 'interface': 1}, # 8: AP
     {'name': 'ec3po_uart',                  # 9: EC3PO(Cr50)
      'raw_pty': 'raw_cr50_console_pty'},
     {'name': 'ec3po_uart',                  #10: EC3PO(EC)
      'raw_pty': 'raw_ec_uart_pty'},
    ]

# Servo micro
SERVO_MICRO_DEFAULTS = [(0x18d1, 0x501a)]
for vid, pid in SERVO_MICRO_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     {'name': 'stm32_uart', 'interface': 0}, # 1: PD/Cr50 console
     'dummy',                                # 2:
     {'name': 'stm32_uart', 'interface': 3}, # 3: servo console
     {'name': 'stm32_i2c', 'interface': 4},  # 4: i2c
     'dummy',                                # 5: dummy
     {'name': 'ec3po_uart',                  # 6: servo console
      'raw_pty': 'raw_servo_console_pty'},
     {'name': 'stm32_uart', 'interface': 6}, # 7: uart1/EC console
     {'name': 'stm32_uart', 'interface': 5}, # 8: uart2/AP console
     {'name': 'ec3po_uart',                  # 9: EC3PO for PD/Cr50
      'raw_pty': 'raw_usbpd_uart_pty'},
     {'name': 'ec3po_uart',                  #10: EC3PO for EC
      'raw_pty': 'raw_ec_uart_pty'},
    ]

# Servo v4
SERVO_V4_DEFAULTS = [(0x18d1, 0x501b)]
SERVO_V4_SLOT_SIZE = 20
SERVO_V4_SLOT_POSITIONS = {
  'default': 1,
  'hammer': 41,
}
SERVO_V4_CONFIGS = {
  'hammer': 'servo_micro_for_hammer.xml',
}
for vid, pid in SERVO_V4_DEFAULTS:
  # Interface #0 is reserved for no use.
  INTERFACE_DEFAULTS[vid][pid] = ['dummy']

  # Dummy slots for servo micro/CCD use (interface #1-20).
  INTERFACE_DEFAULTS[vid][pid] += ['dummy'] * SERVO_V4_SLOT_SIZE

  # Servo v4 interfaces.
  INTERFACE_DEFAULTS[vid][pid] += \
    [{'name': 'stm32_gpio', 'interface': 1}, #21: 32x GPIO block.
     {'name': 'stm32_uart', 'interface': 0}, #22: servo console.
     {'name': 'stm32_i2c', 'interface': 2},  #23: i2c
     {'name': 'stm32_uart', 'interface': 3}, #24: dut sbu uart
     {'name': 'stm32_uart', 'interface': 4}, #25: atmega uart
     {'name': 'ec3po_uart',                  #26: servo v4 console
      'raw_pty': 'raw_servo_v4_console_pty'},
    ]

  # Buffer slots for servo v4 (interface #27-40).
  INTERFACE_DEFAULTS[vid][pid] += ['dummy'] * (40 - 27 + 1)

  # Slots for relocating Hammer interfaces.
  INTERFACE_DEFAULTS[vid][pid] += ['dummy'] * SERVO_V4_SLOT_SIZE

# miniservo
MINISERVO_ID_DEFAULTS = [(0x403, 0x6001), (0x18d1, 0x5000)]
for vid, pid in MINISERVO_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     'ftdi_gpiouart', # occupies 2 slots
     'dummy',         # reserved for the above ftdi_gpiouart
     {'name': 'ec3po_uart', 'raw_pty': 'raw_ec_uart_pty'},
    ]

SERVO_ID_DEFAULTS.extend(MINISERVO_ID_DEFAULTS)

# Toad
TOAD_ID_DEFAULTS = [(0x403, 0x6015)]
for vid, pid in TOAD_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     'ftdi_gpiouart', # occupies 2 slots
     'dummy',         # reserved for the above ftdi_gpiouart
     {'name': 'ec3po_uart', 'raw_pty': 'raw_ec_uart_pty'},
    ]

SERVO_ID_DEFAULTS.extend(TOAD_ID_DEFAULTS)

# Reston
RESTON_ID_DEFAULTS = [(0x18d1, 0x5007)]
for vid, pid in RESTON_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     'ftdi_gpiouart', # occupies 2 slots
     'dummy',         # reserved for the above ftdi_gpiouart
     {'name': 'ec3po_uart', 'raw_pty': 'raw_ec_uart_pty'},
    ]

SERVO_ID_DEFAULTS.extend(RESTON_ID_DEFAULTS)

# Fruitpie
FRUITPIE_ID_DEFAULTS = [(0x18d1, 0x5009)]
for vid, pid in FRUITPIE_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     'ftdi_gpiouart', # occupies 2 slots
     'dummy',         # reserved for the above ftdi_gpiouart
     {'name': 'ec3po_uart', 'raw_pty': 'raw_ec_uart_pty'},
    ]

SERVO_ID_DEFAULTS.extend(FRUITPIE_ID_DEFAULTS)

# Plankton
PLANKTON_ID_DEFAULTS = [(0x18d1, 0x500c)]
for vid, pid in PLANKTON_ID_DEFAULTS:
  INTERFACE_DEFAULTS[vid][pid] = \
    ['dummy',
     'ftdi_gpiouart', # occupies 2 slots
     'dummy',         # reserved for the above ftdi_gpiouart
     {'name': 'ec3po_uart', 'raw_pty': 'raw_ec_uart_pty'},
    ]

SERVO_ID_DEFAULTS.extend(PLANKTON_ID_DEFAULTS)

# Allow Board overrides of interfaces as we've started to overload some servo V2
# pinout functionality.  To-date just swapping EC SPI and JTAG interfaces for
# USB PD MCU UART.  Note this can NOT be done on servo V3.  See crbug.com/567842
# for details.
INTERFACE_BOARDS = collections.defaultdict(
    lambda: collections.defaultdict(dict))

# re-purposes EC SPI to be UART for USBPD MCU
for board in ['elm', 'oak', 'samus']:
  INTERFACE_BOARDS[board][0x18d1][0x5002] = \
      list(INTERFACE_DEFAULTS[0x18d1][0x5002])
  INTERFACE_BOARDS[board][0x18d1][0x5002][6] = 'ftdi_uart'

# re-purposes JTAG to be UART for USBPD MCU or H1
for board in ['asuka', 'caroline', 'cave', 'chell', 'eve', 'glados',
              'kunimitsu', 'lars', 'pbody', 'poppy', 'sentry', 'strago',
              'reef']:
  INTERFACE_BOARDS[board][0x18d1][0x5002] = \
      list(INTERFACE_DEFAULTS[0x18d1][0x5002])
  INTERFACE_BOARDS[board][0x18d1][0x5002][1] = 'ftdi_uart'

# TODO(crosbug.com/p/60939) re-purpose JTAG to H1 uart at some point but dummy
# for now.
for board in ['fizz']:
  INTERFACE_BOARDS[board][0x18d1][0x5002] = \
      list(INTERFACE_DEFAULTS[0x18d1][0x5002])
  INTERFACE_BOARDS[board][0x18d1][0x5002][1] = 'dummy'
