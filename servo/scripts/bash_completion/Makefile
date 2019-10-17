# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk
include $(HDCTOOLS_DIR)/defs/utilities.mk

SCRIPT_DEST_DIR = $(DESTDIR)etc/bash_completion.d

SCRIPT_SRC = $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.bash))
SCRIPT_DST = $(addprefix $(SCRIPT_DEST_DIR)/, $(subst .bash,,$(SCRIPT_SRC)))

$(SCRIPT_DEST_DIR)/%: $(HDCTOOLS_SOURCE_DIR)/%.bash
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

all:
	$(MKDIR) -p $(SCRIPT_DEST_DIR)

install: $(SCRIPT_DST)
