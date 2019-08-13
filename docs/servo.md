# Servo

[TOC]

## Introduction

Servo is a debug board used for Chromium OS test and development. It connects to
most Chrome devices through a debug header on the mainboard. The debug header is
used primarily during development and is often removed before a device is
released to consumers. If you have a production device the debug header might
need reworking before servo can be connected.

Servo is a key enabler for automated testing, including
[automated firmware testing][FAFT]. It provides:

*   Software access to device GPIOs, through `hdctools`
*   Access to EC and CPU UART ports, for convenient debugging
*   Reflashing of EC and system firmware, for easy recovery of bricked systems

For example, it can act as a USB host to simulate connection and removal of
external USB devices. It also provides JTAG/SWD support.

Though Servo boards are not publicly distributed or sold (by Google), detailed
information on [Servo V2 block diagram, BOM, schematic and layout] is available.

## Connecting Servo

In a typical debug setup, you connect servo to the debug header on a Chrome
device, and to a host machine through the HOST_IN USB port. See the annotated
[FAFT setup image] for details.

Most newer Chrome OS mainboards attach to servo with a 50-pin flex cable. The
[schematic and layout for this cable][yoshi_flex] is also available. The
standard DUT-side debug header is an [AXK750347G] from Panasonic, though shorter
variants are sometimes used.

The basic steps to connect servo are:

1.  Check the direction printed on the flex cable.
1.  Connect the DUT end to the debug header on the Chrome device, metal side
    down.
1.  Connect the Servo end to the header on the servo board, metal side up. Make
    sure to engage the black bottom clip of the header on the servo board by
    pushing it inwards after inserting the ribbon cable. This will hold the
    ribbon cable in place and press the contacts.
1.  Use a USB cable to connect the servo board to your Linux workstation.

You should be able to use the power button on servo to power the Chrome device
on and off.

## Using Servo

To use Servo, on your Linux workstation you need to
[build Chromium OS][developer_guide] and create a chroot environment.

The `hdctools` (Chrome OS Hardware Debug & Control Tools) package contains
several tools needed to work with servo. Make sure the latest version is
installed in your chroot:

```bash
(chroot) $ sudo emerge hdctools
```

On your workstation, servod must also be running to communicate with servo:

```bash
(chroot) $ sudo servod -b $BOARD &
```

With `servod` running, `dut-control` commands can be used to probe and change
various controls. For a list of commands, run `dut-control` with no parameters:

```bash
(chroot) $ dut-control
```

You can toggle GPIOs by specifying the control and the state. For example, to
perform a DUT cold reset:

```bash
(chroot) $ dut-control cold_reset:on
(chroot) $ sleep 1
(chroot) $ dut-control cold_reset:off
```

Higher-level controls may set several sub-controls in sequence. For example, to
transition a DUT to recovery mode:

```bash
(chroot) $ dut-control power_state:rec
```

To access the CPU or EC UARTs, first check the port mapping with `dut-control`,
then attach a terminal emulator program to the port:

```bash
(chroot) $ dut-control cpu_uart_pty
(chroot) $ dut-control ec_uart_pty
(chroot) $ sudo minicom -D /dev/pts/$PORT
```

Servo can also be used for flashing firmware. To flash EC firmware:

```bash
(chroot) $ sudo emerge openocd
(chroot) $ /mnt/host/source/src/platform/ec/util/flash_ec --board=$BOARD --image=$IMAGE
```

The procedure for flashing system firmware may vary slightly by platform. Here
is a typical command sequence for flashing system firmware on Baytrail-based
Chrome devices:

```bash
(chroot) $ dut-control spi2_buf_en:on spi2_buf_on_flex_en:on spi2_vref:pp1800 cold_reset:on
(chroot) $ sudo flashrom -V -p ft2232_spi:type=servo-v2 -w $IMAGE # [need to change for each servo type]
(chroot) $ dut-control spi2_buf_en:off spi2_buf_on_flex_en:off spi2_vref:off cold_reset:off
```

To set up servo to run automated tests, connect the servo board and the test
device to the network via Ethernet, and load a Chromium OS image onto USB memory
stick. The networking and build image steps are not described here; see [FAFT]
for details on configuring servo to run automated tests. For information on
writing tests, see the [servo library code] in the [Chromium OS autotest repo].

## Hardware Versions

### Servo v2

*   [Schematic][servo_v2_schematic]
*   [Block Diagram + BOM + Schematic + Layout][servo_v2_diagram_layout]

#### Images

![servo v2 top](https://www.chromium.org/_/rsrc/1410554530438/chromium-os/servo/servo_v2_top.jpg)

![servo v2 bottom](https://www.chromium.org/_/rsrc/1410554549536/chromium-os/servo/servo_v2_bot.jpg)

#### Rework

Servo v2 reworks are needed to flash the PD MCU on certain boards and access
the PD MCU console. These reworks are not mutually compatible, so only apply
the one relevant to your board.

##### samus_pd:

![servo v2 samus_pd rework](https://www.chromium.org/chromium-os/servo/image00.jpg)

##### glados_pd / kunimitsu_pd / chell_pd:

![servo v2 gladus_pd rework](https://www.chromium.org/_/rsrc/1446080772852/chromium-os/servo/IMG_20151019_085815%20%281%29%20%281%29.jpg)

### Servo Micro

Servo Micro is a self-contained replacement for yoshi servo flex. It is meant
to be compatible with servo v2/v3 via `servod`. The design uses case closed
debug software on an STM32 MCU to provide a CCD interface into systems with a
yoshi debug port.

Servo Micro is usually paired with a Servo v4 Type-A, which provides ethernet,
dut hub, and muxed usb storage.

See the detailed documentation in [Servo Micro].

### Servo v4

Servo v4 is the latest test and debug board to work with Google hardware. It
combines Case Closed Debug (CCD) with numerous different methods to download
data to the DUT and other testing and debug functionality.

See the detailed documentation in [Servo v4].

[FAFT]: https://www.chromium.org/for-testers/faft
[Servo V2 block diagram, BOM, schematic and layout]: https://www.chromium.org/chromium-os/servo/chromium_os_servo_v2.tar.gz
[AXK750347G]: http://www3.panasonic.biz/ac/ae/search_num/index.jsp?c=detail&part_no=AXK750347G
[FAFT setup image]: https://www.chromium.org/for-testers/faft/Servo2_with_labels.jpg
[yoshi_flex]: https://www.chromium.org/chromium-os/servo/chromium_os_yoshi_flex.tar.gz
[developer_guide]: https://chromium.googlesource.com/chromiumos/docs/+/master/developer_guide.md
[servo library code]: https://chromium.googlesource.com/chromiumos/third_party/autotest/+/master/server/cros/servo/
[Chromium OS autotest repo]: https://chromium.googlesource.com/chromiumos/third_party/autotest
[servo_v2_schematic]: https://www.chromium.org/chromium-os/servo/810-10010-03_20120227_servo_SCH_0.pdf
[servo_v2_diagram_layout]: https://commondatastorage.googleapis.com/chromeos-localmirror/distfiles/chromium_os_servo_v2.tar.gz
[Servo v4]: ./servo_v4.md
[Servo Micro]: ./servo_micro.md
