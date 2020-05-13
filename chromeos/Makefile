# Copyright 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

INITDIR		= /etc/init
INIT_DEST	= $(DESTDIR)$(INITDIR)

SERVOD_CONF		= servod.conf
UPSTART_SRC		= $(HDCTOOLS_SOURCE_DIR)/$(SERVOD_CONF)
UPSTART_DST		= $(THIS_BUILD_DIR)/$(SERVOD_CONF)

SHAREDIR	= /usr/share/cros
SHARE_DEST	= $(DESTDIR)$(SHAREDIR)
SERVOD_UTILS	= servod_utils.sh
UTIL_SRC	= $(HDCTOOLS_SOURCE_DIR)/$(SERVOD_UTILS)
UTIL_DST	= $(THIS_BUILD_DIR)/$(SERVOD_UTILS)

$(UPSTART_DST): $(UPSTART_SRC)
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(UTIL_DST): $(UTIL_SRC)
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

all:		$(UPSTART_DST) $(UTIL_DST)

install:
	$(MKDIR) -p $(INIT_DEST)
	$(MESSAGE) "Installing '$(SERVOD_CONF)' to $(INIT_DEST)"
	$(CP) $(SERVOD_CONF) "$(INIT_DEST)"
	chmod a+r "$(INIT_DEST)/$(SERVOD_CONF)"

	$(MKDIR) -p $(SHARE_DEST)
	$(MESSAGE) "Installing '$(SERVOD_UTILS)' to $(SHARE_DEST)"
	$(CP) $(SERVOD_UTILS) "$(SHARE_DEST)"
	chmod a+r "$(SHARE_DEST)/$(SERVOD_UTILS)"
