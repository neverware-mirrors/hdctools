# Servo v2

Servo v2 is a debug device in the Servo family. It is no longer manufactured,
but still frequently used for early bringup or in cases where JTAG/SWD is
needed.

[TOC]

## Schematic and Layout

Though Servo boards are not publicly distributed or sold (by Google), detailed
information is available:

*   [Schematic][servo_v2_schematic]
*   [Block Diagram + BOM + Schematic + Layout][servo_v2_diagram_layout]

## Getting Servo v2

*** promo
Sorry, Servo v2 is not publicly available for purchase.
***

### Googlers

Stop by your local Chromestop.

*** note
Since Servo v2 is no longer manufactured, we are more strict about allocation
than other Servo versions.
***

## Connecting Servo v2

In a typical debug setup, you connect Servo v2 to the debug header on a Chrome
OS device, and to a host machine through the `HOST_IN` USB port.

Modern Chrome OS mainboards connect to Servo v2 with a 50-pin "Yoshi" flex
cable. The [schematic and layout for this cable][yoshi_flex] is also available.
The standard DUT-side debug header is an [AXK750347G] from Panasonic, though
shorter variants are sometimes used.

The basic steps to connect Servo v2 are:

1.  Check the direction printed on the Yoshi flex cable.
1.  Connect the DUT end to the debug header on the Chrome OS device, metal side
    down.
1.  Connect the "Servo" end to the header on the Servo v2 board, metal side up.
    Make sure to engage the black bottom clip of the header on the Servo v2
    board by pushing it inwards after inserting the ribbon cable. This will
    hold the ribbon cable in place and press the contacts.
1.  Use a USB cable to connect the Servo v2 board to your Linux workstation.

You should be able to use the power button on Servo v2 to power the Chrome OS
device on and off.

## Using Servo v2

Follow the general [using Servo] instructions.

## Images

![servo v2 top](https://www.chromium.org/_/rsrc/1410554530438/chromium-os/servo/servo_v2_top.jpg)

![servo v2 bottom](https://www.chromium.org/_/rsrc/1410554549536/chromium-os/servo/servo_v2_bot.jpg)

## Rework

Servo v2 reworks are needed to flash the PD MCU on certain boards and access
the PD MCU console. These reworks are not mutually compatible, so only apply
the one relevant to your board.

### samus_pd:

![servo v2 samus_pd rework](https://www.chromium.org/chromium-os/servo/image00.jpg)

### glados_pd / kunimitsu_pd / chell_pd:

![servo v2 gladus_pd rework](https://www.chromium.org/_/rsrc/1446080772852/chromium-os/servo/IMG_20151019_085815%20%281%29%20%281%29.jpg)

[Servo V2 block diagram, BOM, schematic and layout]: https://www.chromium.org/chromium-os/servo/chromium_os_servo_v2.tar.gz
[AXK750347G]: http://www3.panasonic.biz/ac/ae/search_num/index.jsp?c=detail&part_no=AXK750347G
[yoshi_flex]: https://www.chromium.org/chromium-os/servo/chromium_os_yoshi_flex.tar.gz
[servo_v2_schematic]: https://www.chromium.org/chromium-os/servo/810-10010-03_20120227_servo_SCH_0.pdf
[servo_v2_diagram_layout]: https://commondatastorage.googleapis.com/chromeos-localmirror/distfiles/chromium_os_servo_v2.tar.gz
[using Servo]: ./servo.md#using-servo
