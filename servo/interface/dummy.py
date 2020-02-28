# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A dummy interface. This can be used for accounting purposes."""


import interface


class Dummy(interface.Interface):

  @staticmethod
  def Build(**kwargs):
    """Factory method to implement the interface."""
    return Dummy()

  @staticmethod
  def name():
    return "dummy"
