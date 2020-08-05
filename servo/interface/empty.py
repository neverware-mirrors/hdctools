# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A empty interface. This can be used for accounting purposes."""


import interface


class Empty(interface.Interface):

  @staticmethod
  def Build(**kwargs):
    """Factory method to implement the interface."""
    return Empty()

  @staticmethod
  def name():
    return "empty"
