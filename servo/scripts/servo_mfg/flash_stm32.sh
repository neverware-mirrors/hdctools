#!/bin/bash
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

FLAGS_timeout=600
IMG=${1:-sweetberry.bin}

function flash_stm32_dfu() {
        DFU_DEVICE=0483:df11
        ADDR=0x08000000
        DFU_UTIL='dfu-util'
        which $DFU_UTIL &> /dev/null || die \
                "no dfu-util util found.  Did you 'sudo emerge dfu-util'"

        dev_cnt=$(lsusb -d $DFU_DEVICE | wc -l)
        if [ $dev_cnt -eq 0 ] ; then
                die "unable to locate dfu device at $DFU_DEVICE"
        elif [ $dev_cnt -ne 1 ] ; then
                die "too many dfu devices (${dev_cnt}). Disconnect all but one."
        fi

        SIZE=$(wc -c ${IMG} | cut -d' ' -f1)
        # Remove read protection
        timeout -k 10 -s 9 "${FLAGS_timeout}" \
                $DFU_UTIL -a 0 -s ${ADDR}:${SIZE}:force:unprotect -D "${IMG}"
        # Wait for mass-erase and reboot after unprotection
        sleep 1
        # Actual image flashing
        timeout -k 10 -s 9 "${FLAGS_timeout}" \
                $DFU_UTIL -a 0 -s ${ADDR}:${SIZE} -D "${IMG}"
}


flash_stm32_dfu

