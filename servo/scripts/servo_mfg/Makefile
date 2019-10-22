# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk
include $(HDCTOOLS_DIR)/defs/utilities.mk

SUBDIRS		= binfiles
SUBDIRS_INSTALL	= $(foreach var,$(SUBDIRS),$(var)-install)
PYTHON_SRC	= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.py))
PYTHON_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(PYTHON_SRC))
SH_SRC	= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.sh))
SH_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(SH_SRC))

$(THIS_BUILD_DIR)/%.py: $(HDCTOOLS_SOURCE_DIR)/%.py
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(THIS_BUILD_DIR)/%.sh: $(HDCTOOLS_SOURCE_DIR)/%.sh
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

all: 		$(PYTHON_DST) $(SH_DST) $(SUBDIRS)
install:	$(SUBDIRS_INSTALL)

$(SUBDIRS):
	@$(call remake,Building,$@,all)

$(SUBDIRS_INSTALL):
	@$(call remake,Installing,$(subst -install,,$@),install)

.PHONY:	$(SUBDIRS) $(SUBDIRS_INSTALL)
