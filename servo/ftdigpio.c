// Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
#include <assert.h>

#include "ftdi_common.h"
#include "ftdigpio.h"

int fgpio_init(struct fgpio_context *fgc, struct ftdi_context *fc) {
  assert(fgc);
  memset(fgc, 0, sizeof(*fgc));

  fgc->fc = fc;
  fgc->gpio.direction = 0;
  fgc->gpio.value = 0;
  fgc->gpio.mask = 0xff;

  if (fgc->fc->type == TYPE_R) {
    // only a nibble worth of gpios
    fgc->gpio.mask = 0x0f;
  }
  return FGPIO_ERR_NONE;
}

int fgpio_open(struct fgpio_context *fgc, struct ftdi_common_args *fargs) {
  int rv = 0;
  if (!IS_FTDI_OPEN(fgc->fc)) {
    rv = ftdi_usb_open(fgc->fc, fargs->vendor_id, fargs->product_id);
    // TODO(tbroch) investigate rmmod for ftdi_sio and retrying open when the
    // return value is -5 (unable to claim device)
    if (rv < 0) {
      ERROR_FTDI("Opening usb connection", fgc->fc);
      return rv;
    }
  }
  assert(fgc->fc);
  if (fgc->fc->type != TYPE_R) {
    rv = fcom_cfg(fgc->fc, fargs->interface, BITMODE_BITBANG, 0);
  }
  return rv;
}

int fgpio_wr_rd(struct fgpio_context *fgc, struct gpio_s *new_gpio, 
                      uint8_t *rd_val) {
  uint8_t buf[1];
  int dir_chg = 0;
  int val_chg = 0;
  struct ftdi_context *fc = fgc->fc;
  struct gpio_s *gpio = &fgc->gpio;

  if ((gpio->mask | new_gpio->mask) != gpio->mask) {
    prn_error("GPIO mask mismatch 0x%02x != 0x%02x for this interface\n",
              gpio->mask, new_gpio->mask);
    return FGPIO_ERR_MASK;
  }
  // direction register is changing
  if (new_gpio->mask & (gpio->direction ^ new_gpio->direction)) {
    dir_chg = 1;
    gpio->direction = (new_gpio->mask & new_gpio->direction) | 
                      (~new_gpio->mask & gpio->direction);
    prn_dbg("Changing direction register to 0x%02x\n", gpio->direction);
  }
  // value is changing
  if (new_gpio->mask & (gpio->value ^ new_gpio->value)) {
    val_chg = 1;
    gpio->value = (new_gpio->mask & new_gpio->value) | 
                  (~new_gpio->mask & gpio->value);
    prn_dbg("Writing value register to 0x%02x\n", gpio->value);
  }

  if ((fgc->fc->type == TYPE_R) && (val_chg || dir_chg)) {
    buf[0] = ((0xf & gpio->direction)<<4) | (0xf & gpio->value);
    prn_dbg("cbus write of 0x%02x\n", buf[0]);
    CHECK_FTDI(ftdi_set_bitmode(fc, buf[0], BITMODE_CBUS), 
               "write cbus gpio", fc);
  } else {
    if (dir_chg) {
      CHECK_FTDI(ftdi_set_bitmode(fc, gpio->direction, BITMODE_BITBANG), 
                 "re-cfg gpio direction", fc);
    }
    if (val_chg) {
      int wr_bytes = 0;
      buf[0] = (uint8_t) gpio->value;
      wr_bytes = ftdi_write_data(fc, buf, 1);
      if (wr_bytes != 1) {
        ERROR_FTDI("writing gpio data", fc);
        return FGPIO_ERR_WR;
      }
    }
  }
  if (rd_val != NULL) {
    CHECK_FTDI(ftdi_read_pins(fc, rd_val), "reading gpios", fc);
    if (fgc->fc->type == TYPE_R) {
      *rd_val &= 0xf;
    }
  }
  return FGPIO_ERR_NONE;
}

int fgpio_close(struct fgpio_context *fgc) {
  int rv = FGPIO_ERR_NONE;
  CHECK_FTDI(ftdi_disable_bitbang(fgc->fc), "disable bitbang", fgc->fc);
  CHECK_FTDI(ftdi_usb_close(fgc->fc), "usb close", fgc->fc);
  ftdi_deinit(fgc->fc);
  return rv;
}

