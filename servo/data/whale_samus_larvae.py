# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import imp


def _rewrite_control_name(ina):
  """Rewrite the control name in inas[] configs.

  Args:
    ina: config to define one INAx ADC.

  Returns:
    Duplicated config with control name rewritten.
  """
  if type(ina) != tuple:
    raise Exception('Invalid ina definition %r' % adc)
  r = list(ina)
  r[2] = 'whale_' + r[2]
  return tuple(r)


# public attribute of the low-level interface
interface = 2

# Reuse Samus INA config by renaming control name.
_samus_pkg = imp.load_module('samus', *imp.find_module('samus'))
inas = [_rewrite_control_name(ina) for ina in _samus_pkg.inas]
