# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Classes and objects for the Servo Client API.
"""

import re
try:
  from xmlrpclib import ServerProxy, Fault
except ImportError:
  # TODO(crbug.com/999878): This is for python3 compatibility.
  # Remove once fully moved to python3.
  from xmlrpc.client import ServerProxy, Fault

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 9999


class ServoClientError(Exception):
  """Error class for ServoRequest"""

  def __init__(self, text, xmlexc):
    """Constructor for ServoClientError Class

    This class wraps Fault exceptions.

    Args:
      text: a string, error message generated by caller of exception handler
      xmlexc: Fault object supplied by the caught exception. In some
              cases is replaced with None and ignored.

    Fault.faultString has the following format:

    <type 'exception type'>:'actual error message'

    we filter out the actual error message to make it available for the
    downstream exception handler
    """
    if xmlexc:
      xml_error = re.sub('^.*>:', '', xmlexc.faultString)
      err_match = re.match('No control named (\w+)', xml_error)
      if err_match:
        name = err_match.group(1)
        error_msg = 'No control named "%s"\n' % name
        # We know that the second line of the fault text is the comma
        # separated list of all available controls. Let's try finding
        # something similar to what user requested.
        all_controls = xml_error.splitlines()[1]
        candidates = [x for x in all_controls.split(',') if name in x]
        if candidates:
          error_msg += 'Consider %s' % ' '.join(candidates)
      else:
        error_msg = xml_error
      self.message = '%s :: %s' % (text, error_msg)
    else:
      self.message = text


class ServoClient(object):
  """Class to link client to servod via xmlrpc.

  Beyond method initialize, the remaining methods (doc_all, doc, get, get_all,
  set) have a corresponding method implmented in servod's server.
  """

  def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, verbose=False):
    """Constructor for ServoClient Class

    Args:
      host: name or IP address of servo server host
      port: TCP port on which servod is listening on
      verbose: enable verbose messaging across ServerProxy
    """
    self._verbose = verbose
    remote = 'http://%s:%s' % (host, port)
    self._server = ServerProxy(remote, verbose=self._verbose, allow_none=True)

  def doc_all(self):
    """Get the doc string for all controls from servo.

    Returns:
     string of all doc strings of controls from servo.
    """
    return self._server.doc_all()

  def doc(self, name):
    """Get the doc string from servo for control name.

    Args:
      name: string, name of control to retrieve doc string for.

    Returns:
     doc string for control name

    Raises:
      ServoClientError: If error occurs retrieving doc string.
    """
    try:
      return self._server.doc(name)
    except Fault as e:
      raise ServoClientError("Problem docstring '%s'" % name, e)

  def get(self, name):
    """Get the value from servo for control name.

    Args:
      name: string, name of control to get value for.

    Returns:
     value currently set on control name

    Raises:
      ServoClientError: If error occurs getting value.
    """
    try:
      return self._server.get(name)
    except Fault as e:
      raise ServoClientError("Problem getting '%s'" % name, e)

  def get_all(self):
    """Get all controls current values.

    Returns:
      String of all controls and their current values
    """
    return self._server.get_all(self._verbose)

  def set_get_all(self, controls):
    """Set &| get one or more control values.

    Args:
      controls: string, controls to set &| get.

    Raises:
      ServoClientError: If error occurs setting value.
    """
    try:
      rv = self._server.set_get_all(controls)
    except Fault as e:
      # TODO(tbroch) : more detail of failure.  Note xmlrpclib only
      #                passes one exception above
      raise ServoClientError('Problem with %s' % (controls), e)
    return rv

  def set(self, name, value):
    """Set the value from servo for control name.

    Args:
      name: string, name of control to set.
      value: string, value to set control to.

    Raises:
      ServoClientError: If error occurs setting value.
    """
    try:
      self._server.set(name, value)
    except Fault as e:
      # TODO(tbroch) : more detail of failure.  Note xmlrpclib only
      #                passes one exception above
      raise ServoClientError("Problem setting '%s' to '%s'" % (name, value), e)

  def ftdii2c(self, args):
    """Calling a method of Fi2c."""
    self._server.ftdii2c(args)

  def hwinit(self):
    """Initialize the controls."""
    self._server.hwinit()
