# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for common sequences for image management on switchable usb port."""

import glob
import os
import shutil
import subprocess
import tempfile
import time
import urllib

import hw_driver
import servo.utils.usb_hierarchy as usb_hierarchy
import usb


# If a hub is attached to the usual image usb storage slot, use this port on the
# hub to search for the usb storage.
STORAGE_ON_HUB_PORT = 1


class UsbImageManagerError(hw_driver.HwDriverError):
  """Error class for UsbImageManager errors."""
  pass


# pylint: disable=invalid-name
# Servod driver discovery logic requires this naming convension
class usbImageManager(hw_driver.HwDriver):
  """Driver to handle common tasks on the switchable usb port."""

  # Polling rate to poll for image usb dev to appear if setting mux to
  # servo_sees_usbkey
  _POLLING_DELAY_S = 0.1
  # Timeout to wait before giving up on hoping the image usb dev will enumerate
  _WAIT_TIMEOUT_S = 10

  # Timeout to settle all pending tasks on the device before writing to it.
  _SETTLE_TIMEOUT_S = 60

  # Control aliases to the image mux and power intended for image management
  _IMAGE_USB_MUX = 'image_usbkey_mux'
  _IMAGE_USB_PWR = 'image_usbkey_pwr'
  _IMAGE_DEV = 'image_usbkey_dev'
  _IMAGE_MUX_TO_SERVO = 'servo_sees_usbkey'

  _HTTP_PREFIX = 'http://'

  _DEFAULT_ERROR_MSG = 'No USB storage device found for image transfer.'

  def __init__(self, interface, params):
    """Initialize driver by initializing HwDriver."""
    super(usbImageManager, self).__init__(interface, params)
    # This delay is required to safely switch the usb image mux direction
    self._poweroff_delay = params.get('usb_power_off_delay', 0)
    if self._poweroff_delay:
      self._poweroff_delay = float(self._poweroff_delay)
    # This is required to determine if the usbkey is connected to the host.
    # The |hub_ports| is a comma-seperated string of usb hub port numbers
    # that the image usbkey enumerates under for a given servo device.
    # NOTE: initialization here is shared among multiple controls, some of which
    # do not use the hub_ports logic. Do not raise error here if the param
    # is not available, but rather inside the controls that leverage it.
    self._image_usbkey_hub_ports = None
    if 'hub_ports' in params:
      self._image_usbkey_hub_ports = params.get('hub_ports').split(',')
    # Flag to indicate whether the usb port supports having a hub attached to
    # it. In that case, the image will be searched on the |STORAGE_ON_HUB_PORT|
    # of the hub.
    self._supports_hub_on_port = params.get('hub_on_port', False)
    self._error_msg = self._DEFAULT_ERROR_MSG
    if 'error_amendment' in params:
      self._error_msg += ' ' + params['error_amendment']

  def _Get_image_usbkey_direction(self):
    """Return direction of image usbkey mux."""
    return self._interface.get(self._IMAGE_USB_MUX)

  def _Set_image_usbkey_direction(self, mux_direction):
    """Connect USB flash stick to either servo or DUT.

    This function switches 'usb_mux_sel1' to provide electrical
    connection between the USB port J3 and either servo or DUT side.

    Args:
      mux_direction: map values of "servo_sees_usbkey" or "dut_sees_usbkey".
    """
    self._SafelySwitchMux(mux_direction)
    if self._interface.get(self._IMAGE_USB_MUX) == self._IMAGE_MUX_TO_SERVO:
      # This will ensure that we make a best-effort attempt to only
      # return when the block device of the attached usb stick fully
      # enumerates.
      self._interface.get(self._IMAGE_DEV)

  def _SafelySwitchMux(self, mux_direction):
    """Helper to switch the usb mux.

    Switching the usb mux is accompanied by powercycling
    of the USB stick, because it sometimes gets wedged if the mux
    is switched while the stick power is on.

    Args:
      mux_direction: map values of "servo_sees_usbkey" or "dut_sees_usbkey".
    """
    if self._interface.get(self._IMAGE_USB_MUX) != mux_direction:
      self._interface.set(self._IMAGE_USB_PWR, 'off')
      time.sleep(self._poweroff_delay)
      self._interface.set(self._IMAGE_USB_MUX, mux_direction)
      time.sleep(self._poweroff_delay)
    if self._interface.get(self._IMAGE_USB_PWR) != 'on':
      # Enforce that power is supplied.
      self._interface.set(self._IMAGE_USB_PWR, 'on')

  def _PathIsHub(self, usb_sysfs_path):
    """Return whether |usb_sysfs_path| is a usb hub."""
    if not os.path.exists(usb_sysfs_path):
      return False
    with open(os.path.join(usb_sysfs_path, 'bDeviceClass'), 'r') as classf:
      return int(classf.read().strip(), 16) == usb.CLASS_HUB

  def _Get_image_usbkey_dev(self):
    """Probe the USB disk device plugged in the servo from the host side.

    Returns:
      USB disk path if one and only one USB disk path is found, otherwise an
      empty string.

    Raises:
      UsbImageManagerError: if 'hub_ports' was not defined in params
    """
    if self._image_usbkey_hub_ports is None:
      raise UsbImageManagerError('hub_ports need to be defined in params.')
    servod = self._interface
    # When the user is requesting the usb_dev they most likely intend for the
    # usb to the facing the servo, and be powered. Enforce that.
    self._SafelySwitchMux(self._IMAGE_MUX_TO_SERVO)
    # Look for own servod usb device
    # pylint: disable=protected-access
    # Need servod information to find own servod instance.
    usb_id = (servod._vendor, servod._product, servod._serialnames['main'])
    self_usb = usb_hierarchy.Hierarchy.GetUsbDeviceSysfsPath(*usb_id)
    hub_on_servo = usb_hierarchy.Hierarchy.GetSysfsParentHubStub(self_usb)
    # Image usb is one of the hub ports |self._image_usbkey_hub_ports|
    image_location_candidates = ['%s.%s' % (hub_on_servo, p) for p in
                                 self._image_usbkey_hub_ports]
    hub_location_candidates = []
    if self._supports_hub_on_port:
      # Here the config says that |image_usbkey_sysfs| might actually have a hub
      # and not storage attached to it. In that case, the |STORAGE_ON_HUB_PORT|
      # on that hub will house the storage.
      hub_location_candidates = ['%s.%d' % (path, STORAGE_ON_HUB_PORT)
                                 for path in image_location_candidates]
      image_location_candidates.extend(hub_location_candidates)
    self._logger.debug('usb image dev file candidates: %s',
                       ', '.join(image_location_candidates))
    # Let the device settle first before pushing out any data onto it.
    subprocess.call(['/bin/udevadm', 'settle', '-t',
                     str(self._SETTLE_TIMEOUT_S)])
    self._logger.debug('All udev events have settled.')
    end = time.time() + self._WAIT_TIMEOUT_S
    while image_location_candidates:
      active_storage_candidate = image_location_candidates.pop(0)
      if os.path.exists(active_storage_candidate):
        if self._PathIsHub(active_storage_candidate):
          # Do not check the hub, only devices.
          continue
        # Use /sys/block/ entries to see which block device is the |self_usb|.
        # Use sd* to avoid querying any non-external block devices.
        for candidate in glob.glob('/sys/block/sd*'):
          # |candidate| is a link to a sys hw device file
          devicepath = os.path.realpath(candidate)
          # |active_storage_candidate| is also a link to a sys hw device file
          if devicepath.startswith(os.path.realpath(active_storage_candidate)):
            devpath = '/dev/%s' % os.path.basename(candidate)
            if os.path.exists(devpath):
              return devpath
      # Enqueue the candidate again in hopes that it will eventually enumerate.
      image_location_candidates.append(active_storage_candidate)
      if time.time() >= end:
        break
      time.sleep(self._POLLING_DELAY_S)
    # Split and join to help with error message formatting from XML that might
    # introduce multiple white-spaces.
    self._logger.warn(' '.join(self._error_msg.split()))
    self._logger.warn('Stick should be at one of the usb image dev file '
                      'candidates: %s', ', '.join(image_location_candidates))
    if self._supports_hub_on_port:
      self._logger.warn('If using a hub on the image key port, please make '
                        'sure to use port %d on the hub. This should be at '
                        'one of: %s.', STORAGE_ON_HUB_PORT,
                        ', '.join(hub_location_candidates))
    return ''

  def _Get_download_to_usb_dev(self):
    """Improved error reporting for misuse."""
    raise UsbImageManagerError('Download requires image path. Please use set '
                               'version of the control to provide path.')

  def _Set_download_to_usb_dev(self, image_path):
    """Download image and save to the USB device found by host_usb_dev.

    If the image_path is a URL, it will download this url to the USB path;
    otherwise it will simply copy the image_path's contents to the USB path.

    Args:
      image_path: path or url to the recovery image.

    Raises:
      UsbImageManagerError: if download fails for any reason.
    """
    # pylint: disable=broad-except
    # Ensure that any issue gets caught & reported as UsbImageError
    self._logger.debug('image_path(%s)', image_path)
    self._logger.debug('Detecting USB stick device...')
    usb_dev = self._interface.get(self._IMAGE_DEV)
    # |errormsg| is usd later to indicate the error
    errormsg = ''
    if not usb_dev:
      # No usb dev attached, skip straight to the end.
      errormsg = 'No usb device connected to servo'
    else:
      # There is a usb dev attached. Try to get the image.
      try:
        if image_path.startswith(self._HTTP_PREFIX):
          self._logger.debug('Image path is a URL, downloading image')
          urllib.urlretrieve(image_path, usb_dev)
        else:
          shutil.copyfile(image_path, usb_dev)
        # Ensure that after the download the usb-device is still attached, as
        # copyfile does not raise an error stick is removed mid-writing for
        # instance.
        if not self._interface.get('image_usbkey_dev'):
          raise UsbImageManagerError('Device file %s not found again after '
                                     'copy completed.' % usb_dev)
      except urllib.ContentTooShortError:
        errormsg = 'Failed to download URL: %s to USB device: %s' % (image_path,
                                                                     usb_dev)
      except (IOError, OSError) as e:
        errormsg = ('Failed to transfer image to USB device: %s ( %s ) ' %
                    (e.strerror, e.errno))
      except UsbImageManagerError as e:
        errormsg = 'Failed to transfer image to USB device: %s' % e.message
      except BaseException as e:
        errormsg = ('Unexpected exception downloading %s to %s: %s' %
                    (image_path, usb_dev, str(e)))
      finally:
        # We just plastered the partition table for a block device.
        # Pass or fail, we mustn't go without telling the kernel about
        # the change, or it will punish us with sporadic, hard-to-debug
        # failures.
        subprocess.call(['sync'])
        subprocess.call(['blockdev', '--rereadpt', usb_dev])
    if errormsg:
      self._logger.error(errormsg)
      raise UsbImageManagerError(errormsg)

  def _Set_make_image_noninteractive(self, usb_dev_partition):
    """Makes the recovery image noninteractive.

    A noninteractive image will reboot automatically after installation
    instead of waiting for the USB device to be removed to initiate a system
    reboot.

    Mounts |usb_dev_partition| and creates a file called "non_interactive" so
    that the image will become noninteractive.

    Args:
      usb_dev_partition: string of dev partition file e.g. sdb1 or sdc3

    Raises:
     UsbImageManagerError: if error occurred during the process
    """
    # pylint: disable=broad-except
    # Ensure that any issue gets caught & reported as UsbImageError
    if not usb_dev_partition or not os.path.exists(usb_dev_partition):
      msg = 'Usb parition device file provided %r invalid.' % usb_dev_partition
      self._logger.error(msg)
      raise UsbImageManagerError(msg)
    # Create TempDirectory
    tmpdir = tempfile.mkdtemp()
    result = True
    if not tmpdir:
      self._logger.error('Failed to create temp directory.')
      result = False
    else:
      # Mount drive to tmpdir.
      rc = subprocess.call(['mount', usb_dev_partition, tmpdir])
      if rc == 0:
        # Create file 'non_interactive'
        non_interactive_file = os.path.join(tmpdir, 'non_interactive')
        try:
          open(non_interactive_file, 'w').close()
        except IOError as e:
          self._logger.error('Failed to create file %s : %s ( %d )',
                             non_interactive_file, e.strerror, e.errno)
          result = False
        except BaseException as e:
          self._logger.error('Unexpected Exception creating file %s : %s',
                             non_interactive_file, str(e))
          result = False
        # Unmount drive regardless if file creation worked or not.
        rc = subprocess.call(['umount', usb_dev_partition])
        if rc != 0:
          self._logger.error('Failed to unmount USB Device')
          result = False
      else:
        self._logger.error('Failed to mount USB Device')
        result = False

      # Delete tmpdir. May throw exception if 'umount' failed.
      try:
        os.rmdir(tmpdir)
      except OSError as e:
        self._logger.error('Failed to remove temp directory %s : %s', tmpdir,
                           str(e))
        result = False
      except BaseException as e:
        self._logger.error('Unexpected Exception removing tempdir %s : %s',
                           tmpdir, str(e))
        result = False
    if not result:
      raise UsbImageManagerError('Failed to make image noninteractive.')
