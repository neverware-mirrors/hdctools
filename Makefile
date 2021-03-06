# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

export HDCTOOLS_DIR = $(shell pwd)
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		= lib test src servo usbkm232
ifdef EXTRA_DIRS
SUBDIRS		+= $(EXTRA_DIRS)
endif

SUBDIRS_INSTALL	= $(foreach var,$(SUBDIRS),$(var)-install)

all:    $(SUBDIRS)
install:   $(SUBDIRS_INSTALL)
clean:
	@rm -rf $(HDCTOOLS_BUILD_DIR)

$(SUBDIRS): ver
	@$(call remake,Building,$@,all)

# No subdirectory 'install' target needs any dependency on building
# (such as 'all') The explicit dependency on 'all' here ensures that
# the full source tree is built just once.
$(SUBDIRS_INSTALL):	all
	@$(call remake,Installing,$(subst -install,,$@),install)

.PHONY:	ver $(SUBDIRS) $(SUBDIRS_INSTALL)

ver:
	# Generate the sversion file in the same directory as setup.py so that
	# versioning can happen on build-time.
	$(HDCTOOLS_DIR)/getversion.sh > $(HDCTOOLS_DIR)/servo/sversion.py;

src:	lib
test:	src lib
