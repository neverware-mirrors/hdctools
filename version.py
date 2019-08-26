# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess

# Track labstation pushes in the version. Increase this by 1 whenever we do a
# labstation push.
LAB_PUSH_FIELD = 1
# Track major servod features. Increase this by 1 whenever a new feature lands.
MAJOR_FEATURE_FIELD = 0
# TODO(mruthven): make the third field related to commit counts.
THIRD_FIELD = 0

def get_ghash():
  """Get the hash of the latest git commit.

  Returns:
    string of the hash, or 'unknown' if not found.
  """
  try:
    ghash = subprocess.check_output(
        ['git', 'rev-parse', '--short',  '--verify', 'HEAD']).rstrip()
  except:
    # Fall back to the VCSID provided by the packaging system.
    try:
      ghash = os.environ['VCSID'].rsplit('-', 1)[1][:7]
    except:
      ghash = 'unknown'
  return ghash

def get_version_number():
    """Convert lab and major features to a version number."""
    return '%d.%d.%d' % (LAB_PUSH_FIELD, MAJOR_FEATURE_FIELD, THIRD_FIELD)

__version__ = '%s+%s' % (get_version_number(), get_ghash())
