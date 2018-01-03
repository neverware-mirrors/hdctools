# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		=
SUBDIRS_INSTALL	=
XML_SRC		= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.xml))
XML_DST		= $(addprefix $(THIS_BUILD_DIR)/,$(XML_SRC))
PYTHON_SRC	= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.py))
PYTHON_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(PYTHON_SRC))

all: $(PYTHON_DST) $(XML_DST)

$(THIS_BUILD_DIR)/%.py: $(HDCTOOLS_SOURCE_DIR)/%.py
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(THIS_BUILD_DIR)/%.xml: $(HDCTOOLS_SOURCE_DIR)/%.xml
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

install:			# NOP
