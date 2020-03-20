# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Use the generated sversion.py info to provide version strings."""

UNKNOWN_VALUE = 'unknown'

try:
  # pylint: disable=g-import-not-at-top
  # The sversion file might not exist if something goes wrong in the Makefile
  # This just ensures that the system does not break if for some reason
  # version information is missing.
  from . import sversion
  vdict = sversion.VER_DICT
except ImportError:
  # This means that the version dictionary was somehow not generated.
  # This should not break things, rather make a fake dictionary that
  # indicates this issue.
  vdict = {k: UNKNOWN_VALUE for k in ['vbase', 'ghash', 'builder', 'date']}
  vdict['dirty'] = True


def setuptools_version():
  """Geneate a version string given the vdict above."""
  # for setuptools, convert the marker into a '.dev' so that it gets converted
  # properly
  vbase = vdict['vbase']
  if '9999' in vbase:
    # To recognize when the package is being built by cros_workon.
    return '%s.dev' % vbase
  return vbase

def extended_version():
  """More informative version string to use in command-line tools."""
  # The general format here is
  # [vbase][ghash]
  # [date]
  # [builder]
  vbase = setuptools_version()
  return '%s%s\n%s\n%s' % (vbase, vdict['ghash'], vdict['date'],
                           vdict['builder'])
