# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		=
SUBDIRS_INSTALL	=
HEX_SRC	= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.hex))
HEX_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(HEX_SRC))

all: $(HEX_DST) $(BIN_DST)

$(THIS_BUILD_DIR)/%.hex: $(HDCTOOLS_SOURCE_DIR)/%.hex
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

install:			# NOP
