#!/usr/bin/env python2
# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper module to generate system control files."""

import argparse
import copy
import glob
import imp
import json
import os
import re
import sys
import time

class ServoConfigGeneratorError(Exception):
  """Error class for INA control generation errors."""
  pass

class XMLElementGenerator(object):
  """Helper class to generate a formatted XML element.

  Attributes:
    _name: name of the element
    _text: text to go between opening and close brackets
    _attribute_string: string containing attributes and values for element
  """

  def __init__(self, name, text, attributes={}, attribute_order=[]):
    """Prepare substrings to make formatted XML element retrieval easier.

    Args:
      name: name of the element <[name]>.
      text: text to go between opening and closing tag.
      attributes: key/value pairs of attributes for the tag.
      attribute_order: order in which to print the attributes.
    """
    self._name = name
    self._text = text
    keys = [k for k in attribute_order if k in attributes]
    keys += list(set(attributes.keys()) - set(attribute_order))
    self._attribute_string = ''.join(' %s="%s"' %
                                     (k, attributes[k]) for k in keys)

  def GetXML(self, newline_for_text=False):
    """Retrieves XML string for element.

    Args:
      newline_for_text: if |True|, introduce a newline after opening
                        tag and before closing tag.

    Returns:
      formatted string for the element.
    """
    output_format = '<%s%s>\n%s\n</%s>'
    if not newline_for_text:
      output_format.replace('\n', '')
    return output_format % (self._name, self._attribute_string,
                            self._text, self._name)


class ServoControlGenerator(object):
  """Helper class to generate formatted XML for servo controls.

  Attributes:
    _ctrl_elements: list XMLElementGenerators to build control
                    element on retrieval.
  """

  # order of the attributes for the params element.
  params_attr_order = ['cmd', 'interface', 'drv', 'slv',
                       'channel', 'type', 'subtype']

  def __init__(self, name, docstring, params, params2=None):
    """Init an XMLElementGenerator for each element.

    Prepare control XML retrieval by preparing XML generators for each
    component.

    Args:
      name: name tag for the control
      docstring: docstring for the control
      params: attributes for the params tag
      params2: attributes for the 2nd params tag
               (applicable for controls that have both set & get)

    Raises:
      ServoConfigGeneratorError if two malformatted params elements are
      provided.
    """
    parameters = [params]
    if params2:
      # checking to make sure that if there are two paramteter sets, one of them
      # is a set command and the other is a get command.
      if 'cmd' not in params or 'cmd' not in params2:
        raise ServoConfigGeneratorError('Control %s has 2 params. cmd attribute'
                                      ' is required for each param.' % name)
      cmds = set([params['cmd'], params2['cmd']])
      if cmds != set(['get', 'set']):
        raise ServoConfigGeneratorError("Control %s has 2 params, and cmd "
                                      "attributes are not 'set' and 'get'"
                                      % name)
      parameters.append(params2)

    self._ctrl_elements = [XMLElementGenerator('name', name),
                           XMLElementGenerator('doc', docstring)]
    for parameter in parameters:
      self._ctrl_elements.append(XMLElementGenerator('params', '',
                                                     parameter,
                                                     self.params_attr_order))

  def GetControlXML(self):
    """Retrieves XML string for a servod control.

    Returns:
      formatted string for the XML control.
    """
    # for each control element, generate the XML and join together into one
    # string.
    ctrl_text = '\n'.join(element.GetXML() for element in self._ctrl_elements)
    ctrl_element = XMLElementGenerator('control', ctrl_text, {})
    return ctrl_element.GetXML()


class ServoConfigFileGenerator(object):
  """Helper to generate XML servod configuration files.

  Attributes:
    _text: xml file as a string
  """

  XML_VERSION = '1.0'

  def __init__(self, ctrl_generators, includes=None, inline='',
               intro_comments=''):
    """Prepares entire XML file as a string for easier export later.

    Note: use inline carefully as it just gets appended verbatim to the end
    of the config file.

    Args:
      ctrl_generators: ServoControlGenerators for all ctrls in the config file
      inline: string to add verbatim to the config file
      includes: list of xml files to include
      intro_comments: comments to add in the beginning
    """
    self._text = '<?xml version="%s"?>\n' % self.XML_VERSION
    body = ''
    if intro_comments:
      body += '<!-- %s -->\n' % intro_comments
    if includes:
      for include in includes:
        name_element = XMLElementGenerator(name='name', text=include)
        include_tag = XMLElementGenerator(name='include',
                                          text=name_element.GetXML())
        body += '%s\n' % include_tag.GetXML()
    if inline:
      body += '%s\n' % inline
    for generator in ctrl_generators:
      body += generator.GetControlXML()
    file_as_element = XMLElementGenerator(name='root', text=body)
    self._text += file_as_element.GetXML(newline_for_text=True)

  def WriteToFile(self, destination, run_tidy=True):
    """Helper to write to file. Runs tidy after file is written.

    Args:
      destination: dest where to save the file.
      run_tidy: runs tidy if |True|
    """
    with open(destination, 'w') as f:
      f.write(self._text)

    if run_tidy:
      rv = os.system('tidy -quiet -mi -xml %s' % destination)
      if rv:
        raise ServoConfigGeneratorError('Running tidy on %s failed.'
                                      % destination)

  def GetAsString(self):
    """Get entire XML configuration file as a string.

    Returns:
      formatted string for the entire XML config file.
    """
    return self._text
