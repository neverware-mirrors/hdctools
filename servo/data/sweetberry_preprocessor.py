# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""SweetberryPreprocessor enables pin-style sweetberry pwr template writing."""

class SweetberryPreprocessorError(Exception):
  """Error to throw on configuration file syntax issues."""
  pass

class SweetberryPreprocessor(object):
  """Preprocessor to convert pin-style slv-addr config to i2c-addr style.

  See README.sweetberry.md for details. One j-bank on sweetberry has
  16 pin-tuples. Those are organized in blocks of four. Each block has the same
  i2c slave addr. Each slot in a block (e.g. 1st in a block) has the same
  i2c port. This class enables that conversion.
  """

  # Key is the measurement channel. Value is a tuple of (i2c-addr, i2c port).
  sense_chan_i2c_addr = {
      1:    (0x40,3), 2:    (0x40,1), 3:    (0x40,2), 4:    (0x40,0),
      5:    (0x41,3), 6:    (0x41,1), 7:    (0x41,2), 8:    (0x41,0),
      9:    (0x42,3), 10:   (0x42,1), 11:   (0x42,2), 12:   (0x42,0),
      13:   (0x43,3), 14:   (0x43,1), 15:   (0x43,2), 16:   (0x43,0),
      17:   (0x44,3), 18:   (0x44,1), 19:   (0x44,2), 20:   (0x44,0),
      21:   (0x45,3), 22:   (0x45,1), 23:   (0x45,2), 24:   (0x45,0),
      25:   (0x46,3), 26:   (0x46,1), 27:   (0x46,2), 28:   (0x46,0),
      29:   (0x47,3), 30:   (0x47,1), 31:   (0x47,2), 32:   (0x47,0),
      33:   (0x48,3), 34:   (0x48,1), 35:   (0x48,2), 36:   (0x48,0),
      37:   (0x49,3), 38:   (0x49,1), 39:   (0x49,2), 40:   (0x49,0),
      41:   (0x4a,3), 42:   (0x4a,1), 43:   (0x4a,2), 44:   (0x4a,0),
      45:   (0x4b,3), 46:   (0x4b,1), 47:   (0x4b,2), 48:   (0x4b,0)
  }


  # Map to convert from the android connector pin tuple to the channel of that
  # pin-tuple.
  android_conn_pin_to_channel = {
      (7,13):     1,
      (2,8):      2,
      (9,15):     3,
      (4,10):     4,
      (11,17):    5,
      (6,12):     6,
      (19,25):    7,
      (20,26):    8,
      (21,27):    9,
      (22,28):    10,
      (23,29):    11,
      (24,30):    12,
      (37,43):    13,
      (32,38):    14,
      (39,45):    15,
      (34,40):    16,
      (41,47):    17,
      (36,42):    18,
      (49,55):    19,
      (50,56):    20,
      (51,57):    21,
      (52,58):    22,
      (53,59):    23,
      (54,60):    24,
      (67,73):    25,
      (62,68):    26,
      (69,75):    27,
      (64,70):    28,
      (71,77):    29,
      (66,72):    30,
      (79,85):    31,
      (80,86):    32,
      (81,87):    33,
      (82,88):    34,
      (83,89):    35,
      (84,90):    36,
      (97,103):   37,
      (92,98):    38,
      (99,105):   39,
      (94,100):   40,
      (101,107):  41,
      (96,102):   42,
      (109,115):  43,
      (110,116):  44,
      (111,117):  45,
      (112,118):  46,
      (113,119):  47,
      (114,120):  48,
  }

  # Map to convert from the pin tuple to the channel of that pin-tuple for a
  # white j connector.
  j_conn_pin_to_channel = {
      (1,3):    1,
      (2,4):    2,
      (6,8):    3,
      (7,9):    4,
      (11,13):  5,
      (12,14):  6,
      (16,18):  7,
      (17,19):  8,
      (21,23):  9,
      (22,24):  10,
      (26,28):  11,
      (27,29):  12,
      (31,33):  13,
      (32,34):  14,
      (36,38):  15,
      (37,39):  16
  }

  # Map a j-bank to the offset of its first channel to the total
  # number of sense channels.
  j_conn_chan_offset = {
      'j2':  0,
      # The bank j3 starts at channel 17, or one whole j bank later. Thus the
      # offset is the size of one j bank. Same applies to j4 below.
      'j3':  len(j_conn_pin_to_channel),
      'j4':  2 * len(j_conn_pin_to_channel)
  }

  @staticmethod
  def Preprocess(inas):
    """Convert pin-style ina address to i2c slave addr.

    See README.sweetberry.md for details.

    Args:
      inas: list of ina config tuples
      [('sweetberry', (1,3), 'ppvar_some' , 5.0, 0.010, 'j2', False),
       ...]

    Returns:
      list of new ina configuration tuples with i2c slave addresses.
      [('sweetberry', '0x40:3', 'ppvar_some' , 5.0, 0.010, 'j2', False),
       ...]
    """
    #TODO(coconutruben): add an exhaustive unit-test here.
    processed_inas = []
    for (drvname, slv, name, nom, sense, mux, is_calib) in inas:
      if type(slv) is tuple:
        # mux for tuples has to be 'android' or 'j[2,3,4]'
        if mux == 'android':
          pin_to_channel = SweetberryPreprocessor.android_conn_pin_to_channel
          chan_offset = 0
        elif mux in SweetberryPreprocessor.j_conn_chan_offset:
          # mux is one of the known banks: j2, j3, j4.
          pin_to_channel = SweetberryPreprocessor.j_conn_pin_to_channel
          chan_offset = SweetberryPreprocessor.j_conn_chan_offset[mux]
        else:
          raise SweetberryPreprocessorError('mux %s not a valid entry for a '
                                            'pin based config.' % mux)
        sense_chan = pin_to_channel[tuple(sorted(slv))] + chan_offset
        addr, port = SweetberryPreprocessor.sense_chan_i2c_addr[sense_chan]
        slv = '0x%02x:%d' % (addr, port)
      processed_inas.append((drvname, slv, name, nom, sense, mux, is_calib))
    return processed_inas
