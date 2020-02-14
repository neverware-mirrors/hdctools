# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Collection of diagnosis tools for servod."""

import logging

def diagnose_ccd(servo_dev):
  logger = logging.getLogger('CCD-Diagnosis')
  # Voltage levels indicating ~0V or ~3.3V
  NC_LOW = 300
  NC_HIGH = 2800

  # Check ADC values for SBU lines
  sbu1 = int(servo_dev.get('servo_v4_sbu1_mv'))
  sbu2 = int(servo_dev.get('servo_v4_sbu2_mv'))
  # Check ADC values for CC lines
  dut_cc1 = int(servo_dev.get('servo_v4_dut_cc1_mv'))
  dut_cc2 = int(servo_dev.get('servo_v4_dut_cc2_mv'))
  chg_cc1 = int(servo_dev.get('servo_v4_chg_cc1_mv'))
  chg_cc2 = int(servo_dev.get('servo_v4_chg_cc2_mv'))

  # Check SuzyQ routing settings.
  sbu_en = servo_dev.get('sbu_mux_enable') == 'on'  # SuzyQ plugged
  sbu_flip = servo_dev.get('sbu_flip_sel') == 'on'  # SuzyQ flipped
  # Check servo info.
  servo_v4_type = servo_dev.get('servo_v4_type')
  servo_v4_fw = servo_dev.get('servo_v4_version')
  servo_v4_latest_fw = servo_dev.get('servo_v4_latest_version')

  logger.error('')
  logger.error('CCD diagnosis info:')
  logger.error('servo_v4_type is %s' % servo_v4_type)
  logger.error('servo_v4 version is %s' % servo_v4_fw)
  logger.error('')

  # Check for obsolete firmware.
  if servo_v4_fw != servo_v4_latest_fw:
    logger.error("Servo v4 fw version doesn't match latest.")
    logger.error("servo-firmware supplies %s" % servo_v4_latest_fw)
    logger.error("  Run 'sudo servo_updater -b servo_v4' to correct.")
    logger.error('')

  # Check if chargethrough is plugged in.
  if chg_cc1 < NC_LOW and chg_cc2 < NC_LOW:
    logger.error('No charger connected to servo')
    logger.error('')

  # Check if servo v4 is plugged to a DUT.
  if dut_cc1 < NC_LOW and dut_cc2 < NC_LOW:
    logger.error('No DUT plugged into servo')
    logger.error('')
  if dut_cc1 > NC_HIGH and dut_cc2 > NC_HIGH:
    logger.error('No DUT plugged into servo')
    logger.error('')

  # Check if Cr50 USB is present on SBU.
  if sbu1 < NC_LOW and sbu2 < NC_LOW:
    logger.error('No USB exported from DUT Cr50')
    logger.error('')

  cr50_orientation = None
  if sbu1 > NC_HIGH and sbu2 < NC_LOW:
    cr50_orientation = 'flip'
  if sbu1 < NC_LOW and sbu2 > NC_HIGH:
    cr50_orientation = 'direct'

  suzyq_orientation = 'flip' if sbu_flip else 'direct'

  # Check if Cr50 orientation seems flipped from SuzyQ.
  if cr50_orientation:
    logger.error('Cr50 USB detected in '
        '%s orientation' % cr50_orientation)
    logger.error('SuzyQ in %s orientation' % suzyq_orientation)
    logger.error('')

  # Check if SuzyQ routed to DUT.
  if not sbu_en:
    logger.error('SuzyQ disabled in software')
    logger.error('')

  # Dump raw voltages and settings.
  logger.error('DUT CC: %4dmV %4dmV' % (dut_cc1, dut_cc2))
  logger.error('CHG CC: %4dmV %4dmV' % (chg_cc1, chg_cc2))
  logger.error('SBU:    %4dmV %4dmV' % (sbu1, sbu2))
  logger.error('SuzyQ enabled: '
      '%s, SuzyQ orientation: %s' % (sbu_en, suzyq_orientation))
  logger.error('')

