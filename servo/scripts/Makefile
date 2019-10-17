# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk
include $(HDCTOOLS_DIR)/defs/utilities.mk

SUBDIRS		= servo_mfg bash_completion
SUBDIRS_INSTALL	= $(foreach var,$(SUBDIRS),$(var)-install)

all: 		$(SUBDIRS)
install:	$(SUBDIRS_INSTALL)

$(SUBDIRS):
	@$(call remake,Building,$@,all)

$(SUBDIRS_INSTALL):
	@$(call remake,Installing,$(subst -install,,$@),install)

.PHONY:	$(SUBDIRS) $(SUBDIRS_INSTALL)
