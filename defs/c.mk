# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file contains definitions which control the C compiler.
ifndef CC
$(warning CC not defined; assuming gcc.)
CC	= $(GCC)
endif

CFLAGS	?=					\
	-g					\
	-O2


# # Compiler is too old to support
# #
# #	-Wframe-larger-than=256
# #	-Wlarger-than=4096
# #	-Wsync-nand

# # Enable GC on unused functions and data
# CGC	=					\
# 	-ffunction-sections			\
# 	-fdata-sections

# Also need to link with '-Xlinker --library=pthread'.
PTHREAD	= 					\
	-pthread

# LDGC	=					\
# 	-Xlinker --gc-sections


#  TBD: These need code changes to enable.
#	-Wconversion				\
#	-Wmissing-noreturn			\
#	-Wsign-conversion			\
#	-Wtraditional-conversion		\

# The host 'c-$(HDCTOOLS_OS_NAME).mk' file can define the following
# variables.
#
#  HOSTOS_CWARN   : A set of compiler flags which turn on the desired
#                   warnings.
#
#  HOSTOS_INCLUDE : A set of compiler flags which add directories to the
#                   standard #include search path.
#
#  HOSTOS_LD_LIB  : A set of host-os specific values for 'LD_LIB'.
#
#  HOSTOS_LIB_EXT : A set of host-os specific values for 'LIB_EXT'
#
#  HOSTOS_CFLAGS  : A set of host-os specific compiler flags
#
#  HOSTOS_CPPFLAGS: A set of host-os specific preprocessor defines.
#
include $(HDCTOOLS_DIR)/defs/c-$(HDCTOOLS_OS_NAME).mk

CWARN	=					\
	$(HOSTOS_CWARN)

INCLUDES	=				\
		$(HOSTOS_INCLUDE)		\
		-I$(HDCTOOLS_DIR)/include	\
		-I$(HDCTOOLS_SOURCE_DIR)

LD_LIB		= $(HOSTOS_LD_LIB)
LIB_EXT		= $(HOSTOS_LIB_EXT)

ifeq ($(DEBUG),1)
  CDEBUG	= -DDEBUG
endif

CPPFLAGS	+=				\
	$(HOSTOS_CPPFLAGS) 			\
	-D_GNU_SOURCE=1				\
	$(INCLUDES)

CFLAGS 	+=					\
	-std=gnu99				\
	-MMD					\
	$(PTHREAD)				\
	$(CWARN)				\
	$(CGC)					\
	$(LDGC)					\
	$(CDEBUG)				\
	$(HOSTOS_CFLAGS)

COMPILE.c	= \
	$(MESSAGE) "Compiling $(notdir $<)" ; \
	$(CC) $(CFLAGS) $(CPPFLAGS) -c -o $@ $<
LINK.c		= \
	$(MESSAGE) "Linking $(notdir $@)" ; \
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LDLIBS)

FTDIVERSION = $(shell $(PKG_CONFIG) --modversion libftdi1 2>/dev/null)
ifneq ($(FTDIVERSION),)
  LIBFTDI_NAME = ftdi1
else
  LIBFTDI_NAME = ftdi
endif
LIBFTDI_CFLAGS	:= \
	$(shell $(PKG_CONFIG) --cflags lib${LIBFTDI_NAME}) \
	$(shell $(PKG_CONFIG) --atleast-version=1.2 lib${LIBFTDI_NAME} && \
		echo "-DSUPPORT_TYPE_230X")
LIBFTDI_LDLIBS	:= $(shell $(PKG_CONFIG) --libs   lib${LIBFTDI_NAME})

SERIAL_IP	= gpio uart i2c
SERIAL_LIBS	= $(foreach v,${SERIAL_IP},-lftdi$(v))

