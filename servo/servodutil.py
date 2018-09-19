# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Collection of servod utilities."""

import argparse
import collections
import json
import logging
import os
import re
import signal
import socket
import sys

import client
import usb


class ServodUtilError(Exception):
  """General servodutil error class."""
  pass


class UsbHierarchy(object):
  """A helper class to analyze the sysfs hierarchy of USB devices."""

  USB_SYSFS_PATH = '/sys/bus/usb/devices'
  CHILD_RE = re.compile(r'\d+-\d+(\.\d+){1,}\Z')
  BUS_FILE = 'busnum'
  DEV_FILE = 'devnum'

  def __init__(self):
    # Get the current USB sysfs hierarchy.
    self.RefreshUsbHierarchy()

  @staticmethod
  def GetAllUsbDevices(vid_pid_list):
    """Return all associated USB devices which match the given VID/PID's.

    Args:
      vid_pid_list: List of tuple (vid, pid).

    Returns:
      List of usb.core.Device objects.
    """
    all_devices = []
    for vid, pid in vid_pid_list:
      devs = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
      if devs:
        all_devices.extend(devs)
    return all_devices

  @staticmethod
  def GetUsbDevice(vid, pid, serial):
    """Given vendor id, product id, and serial return usb device object.

    Args:
      vid: vendor id
      pid: product id
      serial: serial name

    Returns:
      usb.core.Device object if found otherwise None

    Raises:
      ServodUtilError: if more than one device are found with those attributes.
    """
    devices = UsbHierarchy.GetAllUsbDevices([(vid, pid)])
    devs = []
    for device in devices:
      d_serial = usb.util.get_string(device, 256, device.iSerialNumber)
      if d_serial == serial:
        devs.append(device)
    if len(devs) > 1:
      raise ServodUtilError('Found %d devices with |vid:%s|, |pid:%s|, '
                            '|serial:%s|. Should not happen.' % (len(devs),
                                                                 str(vid),
                                                                 str(pid),
                                                                 str(serial)))
    return devs[0] if devs else None

  @staticmethod
  def _ResolveUsbSysfsPath(path):
    if not os.path.isabs(path):
      path = os.path.join(UsbHierarchy.USB_SYSFS_PATH, path)
    return path

  @staticmethod
  def DevNumFromSysfs(sysfs_path):
    path = UsbHierarchy._ResolveUsbSysfsPath(sysfs_path)
    devfile = os.path.join(path, UsbHierarchy.DEV_FILE)
    with open(devfile, 'r') as devf:
      return int(devf.read().strip())

  @staticmethod
  def BusNumFromSysfs(sysfs_path):
    path = UsbHierarchy._ResolveUsbSysfsPath(sysfs_path)
    busfile = os.path.join(path, UsbHierarchy.BUS_FILE)
    with open(busfile, 'r') as busf:
      return int(busf.read().strip())

  def RefreshUsbHierarchy(self):
    """Walk through usb sysfs files and gather parent identifiers.

    The usb sysfs dir contains dirs of the following format:
    - 1-2
    - 1-2:1.0
    - 1-2.4
    - 1-2.4:1.0

    The naming convention works like so:
      <roothub>-<hub port>[.port[.port]]:config.interface

    We are only going to be concerned with the roothub, hub port and port.
    We are going to create a hierarchy where each device will store the usb
    sysfs path of its roothub and hub port.  We will also grab the device's
    bus and device number to help correlate to a usb.core.Device object.

    We will walk through each dir and only match on device dirs
    (e.g. '1-2.4') and ignore config.interface dirs.  When we get a hit, we'll
    grab the bus/dev and infer the roothub and hub port from the dir name
    ('1-2' from '1-2.4') and store the info into a dict.

    The dict key will be a tuple of (bus, dev) and value be the sysfs path.

    Returns:
      Dict of tuple (bus,dev) to sysfs path.
    """
    usb_hierarchy = collections.defaultdict(lambda: (None, None))
    for usb_dir in os.listdir(self.USB_SYSFS_PATH):
      if self.CHILD_RE.match(usb_dir):
        usb_dir = os.path.join(self.USB_SYSFS_PATH, usb_dir)
        # Remove last element to get to parent hub's location
        parent = '.'.join(usb_dir.split('.')[:-1])
        try:
          dev = UsbHierarchy.DevNumFromSysfs(usb_dir)
          bus = UsbHierarchy.BusNumFromSysfs(usb_dir)
        except IOError:
          # This means no bus/dev files. Skip
          continue

        usb_hierarchy[(bus, dev)] = (usb_dir, parent)

    self._usb_hierarchy = usb_hierarchy

  def GetPath(self, usb_device):
    """Return the USB sysfs path of the supplied usb_device.

    Args:
      usb_device: usb.core.Device object.

    Returns:
      SysFS path string of parent of the supplied usb device,
      or None if not found.
    """
    return self._usb_hierarchy.get((int(usb_device.bus),
                                    int(usb_device.address)))[0]

  def GetParentPath(self, usb_device):
    """Return the USB sysfs path of the supplied usb_device's parent.

    Args:
      usb_device: usb.core.Device object.

    Returns:
      SysFS path string of parent of the supplied usb device,
      or None if not found.
    """
    return self._usb_hierarchy.get((int(usb_device.bus),
                                    int(usb_device.address)))[1]

  def ShareSameHub(self, usb_servo, usb_candidate):
    """Check if the given USB device shares the same hub with servo v4.

    Args:
      usb_servo: usb.core.Device object of servo v4.
      usb_candidate: usb.core.Device object of USB device canditate.

    Returns:
      True if they share the same hub; otherwise, False.
    """
    usb_servo_parent = self.GetParentPath(usb_servo)
    usb_candidate_parent = self.GetParentPath(usb_candidate)

    if usb_servo_parent is None or usb_candidate_parent is None:
      return False

    # Check the hierarchy:
    #   internal hub <-- servo v4 mcu
    #         \--------- USB candidate
    if usb_servo_parent == usb_candidate_parent:
      return True

    # Check the hierarchy:
    #   internal hub <-- servo v4 mcu
    #         \--------- external hub
    #                          \--------- USB candidate
    # Check having '.' to make sure it is one of the ports of the internal hub.
    if usb_candidate_parent.startswith(usb_servo_parent + '.'):
      return True

    return False


SERVO_SCRATCH_DIR = '/tmp/servoscratch'

# order used to print information
ORDER = ['port', 'serials', 'pid']

PORT_RANGE = (9990, 9999)


def _FormatInfo(info):
  """Output format helper that turns a dictionary into 'key: value' lines."""
  output_lines = ['%s : %s' % (val, info[val]) for val in ORDER]
  return '\n'.join(output_lines)


class ServoScratch(object):
  """Class to manage servod instance breadcrumbs used to query and control.

  Attributes:
    _logger: logger
    _scratch: directory to leave information in.
  """

  _NO_FOUND_WARNING = 'No servod scratch entry found under id: %r.'

  def __init__(self, scratch=SERVO_SCRATCH_DIR):
    """Initialize utility by creating |scratch| if necessary.

    Args:
      scratch: directory to write servod info into.

    Note:
      Unless for good reason (test, special setup) scratch should be left as
      its default.
    """
    self._scratch = scratch
    self._logger = logging.getLogger('ServoScratch')
    self._logger.setLevel(logging.DEBUG)
    if not os.path.exists(self._scratch):
      os.makedirs(self._scratch)
    self._Sanitize()

  def AddEntry(self, port, serials, pid):
    """Register information about servod instance.

    Args:
      port: port servod is being served
      serials: list of serialnames for devices being served through instance
      pid: pid of the main servod process

    Raises:
      ServodUtilError: if port or pid aren't int convertible or serials isn't
      list convertible, if port or any serial in serials already has an entry
    """
    entryf = os.path.join(self._scratch, str(port))
    # TODO(coconutruben): add cmdline support
    try:
      entry = {'port': int(port),
               'serials': list(serials),
               'pid': int(pid)}
    except (ValueError, TypeError):
      raise ServodUtilError('Entry arguments malformed.')
    if os.path.exists(entryf):
      msg = 'Adding entry for port already in use. Port: %d.' % int(port)
      self._logger.error(msg)
      raise ServodUtilError(msg)
    serialfs = []
    for serial in entry['serials']:
      serialf = os.path.join(self._scratch, str(serial))
      if os.path.exists(serialf):
        # Add a symlink for each serial pointing back at the original file
        msg = 'Adding entry in %s for serial already in use. Serial: %s.' % (
               serialf, serial)
        self._logger.error(msg)
        raise ServodUtilError(msg)
      serialfs.append(serialf)

    with open(entryf, 'w') as f:
      json.dump(entry, f)

    for serialf in serialfs:
      os.symlink(entryf, serialf)

  def RemoveEntry(self, identifier):
    """Remove information about servod instance.

    Args:
      identifier: either port where servod is being served, or a serial number
                  of one of the servod devices being served by instance
    """
    entryf = os.path.realpath(os.path.join(self._scratch,
                                           str(identifier)))
    if not os.path.exists(entryf):
      self._logger.warn('No entry available for id: %s. Ignoring.', identifier)
      return
    for f in os.listdir(self._scratch):
      fullf = os.path.join(self._scratch, f)
      if os.path.islink(fullf) and os.path.realpath(fullf) == entryf:
        os.remove(fullf)
    os.remove(entryf)

  def FindById(self, identifier):
    """Find and load servod instance info for identifier.

    Args:
      identifier: either port where servod is being served, or a serial number
                  of one of the servod devices being served by instance

    Returns:
      dictionary containing 'port', 'serials', and 'pid' of instance

    Raises:
      ServodUtilError: if no entry found under |indentifier| or if entry found
                       is invalid json
    """
    entryf = os.path.join(self._scratch, str(identifier))
    if not os.path.exists(entryf):
      raise ServodUtilError(self._NO_FOUND_WARNING % identifier)
    with open(entryf, 'r') as f:
      try:
        entry = json.load(f)
      except ValueError:
        # Invalid json file
        os.remove(entryf)
        raise ServodUtilError('id: %s had invalid json formatting. Removed.' %
                              identifier)
    return entry

  def Show(self, args):
    """Print info of servod instance found by -p/-s args."""
    try:
      entry = self.FindById(args.id)
      self._logger.info(_FormatInfo(entry))
    except ServodUtilError:
      self._logger.info(self._NO_FOUND_WARNING, args.id)

  def _GetAllEntries(self):
    """Find and load servod instance info for all registered servod instances.

    Returns:
      List of dictionaries containing 'port', 'serials', and 'pid' of instance
    """
    entries = []
    for f in os.listdir(self._scratch):
      entryf = os.path.join(self._scratch, f)
      if os.path.islink(entryf):
        continue
      with open(entryf, 'r') as f:
        try:
          entries.append(json.load(f))
        except ValueError:
          self._logger.warn('Removing file %r as it contains invalid JSON.',
                            entryf)
          # Invalid json file
          os.remove(entryf)
    return entries

  def ShowAll(self, _):
    """Print info of all registered servod instances."""
    output_lines = [_FormatInfo(entry) for entry in self._GetAllEntries()]
    if output_lines:
      self._logger.info('\n---\n'.join(output_lines))
    else:
      self._logger.info('No entries found.')

  def Stop(self, args):
    """Stop servod instance found by -i/--identifier arg.

    Servod handles the cleanup code to remove its own entry.

    Args:
      args: args from cmdline argument with id attribute,
            id is either a port or serial number used to find servod scratch
            entry
    """
    try:
      entry = self.FindById(args.id)
      os.kill(entry['pid'], signal.SIGTERM)
      self._logger.info('SIGTERM sent to servod instance associated with %r.',
                        args.id)
    except ServodUtilError:
      self._logger.info(self._NO_FOUND_WARNING, args.id)

  def _GenerateEntryFromPort(self, port):
    """Given a port number, try to generate an entry from it.

    Tries to ask servod instance for information to retroactively
    add an entry.

    Args:
      port: port where the alleged servod instance is listening

    Returns:
      True if entry successfully rebuilt, False otherwise
    """
    # pylint: disable=protected-access
    msg = 'nonsense'
    expected_output = 'ECH0ING: %s' % msg
    try:
      sclient = client.ServoClient(port=port)
      if sclient._server.echo(msg) == expected_output:
        self._logger.warn('Port %r not registered but has a servod '
                          'instance bound to it. Retroactively adding the '
                          'instance.', port)
        serials = sclient._server.get_servo_serials()
        serials = list(serials.itervalues())
        pid = sclient.get('servod_pid')
        self.AddEntry(port=port, serials=serials, pid=pid)
        return True
    except socket.error:
      # expected to fail as no servod instance should be running on an
      # untracked port.
      return False
    except ServodUtilError:
      # Don't rebuild an entry if the entry already exists.
      return False

  def Rebuild(self, args):
    """Rebuild servodscratch.

    If for some reason the scratch has gotten into a bad state, this can be used
    to attempt to rebuild entries. If |args.port| is a port, then attempt
    to specifically rebuild that port. Otherwise, attempt to rebuild each
    port in the default port range that is not a known entry.

    Args:
      args: parser namespace that should contain |port|,
            port is either None or a port number
    """
    if args.port:
      port = args.port
      if not self._GenerateEntryFromPort(port):
        self._logger.error('Could not rebuild entry for port %r', port)
      return
    # PORT_RANGE[1] + 1 as PORT_RANGE[1] should be in the set.
    ports = set(range(PORT_RANGE[0], PORT_RANGE[1] + 1))
    ports -= set([entry['port'] for entry in self._GetAllEntries()])
    for port in ports:
      # GenerateEntryFromPort will attempt to generate a new entry if
      # a ServoClient can be bound to |port|.
      self._GenerateEntryFromPort(port)

  def _Sanitize(self):
    """Verify that all known servod ports are still in use, delete otherwise."""
    testsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for entry in self._GetAllEntries():
      port = entry['port']
      try:
        testsock.bind(('localhost', port))
        self._logger.warn('Port %r still registered but not bound to a '
                          'servod instance. Removing entry.', str(port))
        self.RemoveEntry(port)
      except socket.error:
        # Expected to fail when binding to a valid servod instance socket.
        pass
    testsock.close()


# pylint: disable=invalid-name
def _ConvertNameToMethod(name):
  """Convert dash separated words to camelcase."""
  parts = name.split('-')
  return ''.join([w.capitalize() for w in parts])


# pylint: disable=dangerous-default-value
def main(cmdline=sys.argv[1:]):
  """Entry function for cmdline servodutil tool."""
  # pylint: disable=protected-access
  scratchutil = ServoScratch()
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.INFO)
  scratchutil._logger.addHandler(stdout_handler)
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(dest='command')
  show = subparsers.add_parser('show',
                               help='show information on servod instance')
  stop = subparsers.add_parser('stop',
                               help='gracefully stop servod instance')
  # TODO(coconutruben): build out restart function
  for p in [show, stop]:
    id_group = p.add_mutually_exclusive_group(required=True)
    id_group.add_argument('-s', '--serial', dest='id',
                          help='serial of servo device on associated servod.')
    id_group.add_argument('-p', '--port', dest='id',
                          help='port where servod instance is listening.')
  rebuild = subparsers.add_parser('rebuild', help='try to rebuild entry for '
                                  'servod running on a given port. If no '
                                  'specific port provided, attempts default '
                                  'servod port range.')
  rebuild.add_argument('-p', '--port', default=None,
                       help='port to rebuild.')
  subparsers.add_parser('show-all', help='show info on all servod instances')
  args = parser.parse_args(cmdline)
  cmd = _ConvertNameToMethod(args.command)
  getattr(scratchutil, cmd)(args)

if __name__ == '__main__':
  main()
