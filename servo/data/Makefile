# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		=
SUBDIRS_INSTALL	=
XML_SRC		= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.xml))
XML_DST		= $(addprefix $(THIS_BUILD_DIR)/,$(XML_SRC))
INAS		= wario.xml waluigi.xml servo_loc.xml link_dvt.xml link.xml    \
		  snow.xml daisy.xml mccroskey.xml spring_v0_r0.xml spring.xml \
		  pi.xml pit.xml falco.xml peppy.xml rambi.xml nyan.xml \
		  samus_p1.xml rambi_1v5_r0_loc.xml rambi_2v0_r0_loc.xml \
		  skate.xml big.xml whale_samus_larvae.xml storm.xml \
		  veyron_p0.xml veyron_p1.xml veyron_r2.xml samus_evt_v1.xml \
		  strago_proto.xml veyron_danger_p1.xml ryu_p0_loc.xml oak.xml \
		  veyron_brain_p1.xml ryu_p5_loc.xml ryu_evt2_loc.xml \
		  ryu_dvt_loc.xml kunimitsu.xml amenia_inas.xml kevin_r0_loc.xml \
		  kevin_r1_loc.xml kevin_r2_loc.xml caroline_evt_loc.xml \
                  samus.xml whale_samus_dut.xml gru_r0.xml servo_v4_inas.xml \
                  glados_p1_inas.xml glados_r2_inas.xml chell_r1_inas.xml \
                  reef_r1_inas.xml eve_r0_inas.xml poppy_r0.xml \
                  poppy_r1_r2.xml poppy_r3.xml eve_p1_loc.xml hammer.xml \
                  eve_evt_inas.xml eve_evt_loc.xml scarlet_r1_loc.xml \
                  eve_evtb_loc.xml eve_dvt_loc.xml eve_dvt2_loc.xml \
                  kahlee_inas.xml fizz.xml coral.xml whiskers.xml \
                  scarlet_r2_loc.xml

# TODO(tbroch) should probably be added to setup.py if possible
all:	$(INAS) $(XML_DST)

$(THIS_BUILD_DIR)/%.xml: $(HDCTOOLS_SOURCE_DIR)/%.xml
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(INAS): %.xml:%.py
	$(MESSAGE) "Building $@"
	python2 -B "$(HDCTOOLS_SOURCE_DIR)/generate_ina_controls.py" \
		$(basename $(<F))

install:			# NOP
