# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""SweetberryPreprocessor enables pin-style sweetberry pwr template writing."""

class SweetberryPreprocessor(object):
  """Preprocessor to convert pin-style slv-addr config to i2c-addr style.

  See README.sweetberry.md for details. One j-bank on sweetberry has
  16 pin-tuples. Those are organized in blocks of four. Each block has the same
  i2c slave addr. Each slot in a block (e.g. 1st in a block) has the same
  i2c port. This class enables that conversion.
  """

  # map to convert from the pin tuple to the 'index' of that pin-tuple
  index_lookup = {
      (1,3):  0,
      (2,4):  1,
      (6,8):  2,
      (7,9):  3,
      (11,13):4,
      (12,14):5,
      (16,18):6,
      (17,19):7,
      (21,23):8,
      (22,24):9,
      (26,28):10,
      (27,29):11,
      (31,33):12,
      (32,34):13,
      (36,38):14,
      (37,39):15
  }

  # sweetberry i2c ports used for one j-bank. Index into this list with the
  # index's position inside of an index block gives the port for the index.
  port_lookup = [3,1,2,0]

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
        #mux for tuples has to be j2, j3, or j4
        bank = int(mux[1:])
        pins = tuple(sorted(slv))
        index = SweetberryPreprocessor.index_lookup[pins]
        #j2 starts at 0x40, j3 at 0x44, j4 at 0x48. This allows for easy math.
        bank_base = 0x38 + bank * 4
        # the slv addr is the base for a bank + the index block on that bank
        slv_addr = bank_base + index / 4
        # the port is the defined by the slot of the index inside an index block
        port = SweetberryPreprocessor.port_lookup[index % 4]
        slv = '0x%02x:%d' % (slv_addr, port)
      processed_inas.append((drvname, slv, name, nom, sense, mux, is_calib))
    return processed_inas

