# Servo

[TOC]

## Introduction

Servo is a debug board used for Chromium OS test and development. Depending on
the version of Servo, it can connect to a debug header or USB port on the
Chrome OS device. The debug header is used primarily during development and is
often removed before a device is released to consumers.

Servo is a key enabler for automated testing, including
[automated firmware testing][FAFT]. It provides:

*   Software access to device GPIOs, through `hdctools`
*   Access to EC and CPU UART ports, for convenient debugging
*   Reflashing of EC and system firmware, for easy recovery of bricked systems

For example, it can act as a USB host to simulate connection and removal of
external USB devices. It also provides JTAG/SWD support.

Though Servo boards are not publicly distributed or sold (by Google),
schematics and layout for each version is available.

## Hardware Versions

### Servo v2

See the detailed documentation in [Servo v2].

### Servo Micro

Servo Micro is a self-contained replacement for Yoshi Servo flex. It is meant
to be compatible with Servo v2/v3 via `servod`. The design uses case closed
debug software on an STM32 MCU to provide a [CCD] interface into systems with a
Yoshi debug port.

Servo Micro is usually paired with a Servo v4 Type-A, which provides ethernet,
dut hub, and muxed usb storage.

See the detailed documentation in [Servo Micro].

### Servo v4

Servo v4 is the latest test and debug board to work with Google hardware. It
combines Case Closed Debug ([CCD]) with numerous different methods to download
data to the DUT and other testing and debug functionality.

See the detailed documentation in [Servo v4].

## Using Servo {#using-servo}

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
*** note
WARNING: `servod` must be run inside a chroot that was launched with the
`--no-ns-pid` flag. [It is annoying to always specify this (or
forget)][servod_no_nspid], so you may want to add this to your `$HOME/.bashrc`:

```bash
alias cros_sdk='cros_sdk --no-ns-pid'
```
***

With `servod` running, `dut-control` commands can be used to probe and change
various controls. For a list of commands, run `dut-control` with no parameters:

```bash
(chroot) $ dut-control
```

You can toggle GPIOs by specifying the control and the state.

Perform a DUT cold reset:

```bash
(chroot) $ dut-control cold_reset:on
(chroot) $ sleep 1
(chroot) $ dut-control cold_reset:off
```

Power-cycle a DUT:

```bash
(chroot) $ dut-control power_state:off
(chroot) $ dut-control power_state:on
```

Higher-level controls may set several sub-controls in sequence.

For example, to transition a DUT to recovery mode:

```bash
(chroot) $ dut-control power_state:rec
```

To read the value of a `dut-control` property, just specify the name of the
property:

```bash
(chroot) $ dut-control <name_of_property>
```

For example, to access the CPU or EC UARTs, first check the port mapping with
`dut-control`, then attach a terminal emulator program to the port:

```bash
(chroot) $ dut-control cpu_uart_pty
(chroot) $ dut-control ec_uart_pty
(chroot) $ sudo minicom -D /dev/pts/$PORT
```

To see all the available `dut-control` commands, you can do:

```bash
(chroot) $ dut-control --info
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

## Using multiple servos on the same machine

It's possible to connect multiple servos at once, which is especially useful
for testing/developing against multiple devices. Servo v4 will charge the DUT
if a charger is attached to it and also provides an ethernet jack so SSH is
always available.

To use multiple servos, you need to run multiple instances of `servod`, each
running on a different port. You also need to specify the servo's serial name.

To find the serialname of connected servos:

```bash
(chroot) $ sudo servod
```

Look for `sid`:

```bash
2019-05-16 13:28:40,301 - servod - INFO - Start
2019-05-16 13:28:40,384 - servod - INFO - Found servo, vid: 0x18d1 pid: 0x5002 sid: 911416-00789
2019-05-16 13:28:40,386 - servod - INFO - Found servo, vid: 0x18d1 pid: 0x5002 sid: 911416-00927
2019-05-16 13:28:40,389 - servod - INFO - Found servo, vid: 0x18d1 pid: 0x5014 sid: 0601002A-922A4826
2019-05-16 13:28:40,389 - servod - INFO - Found servo, vid: 0x18d1 pid: 0x501b sid: C1804020116
2019-05-16 13:28:40,389 - servod - INFO -
2019-05-16 13:28:40,391 - servod - INFO - Press '0' for servo, vid: 0x18d1 pid: 0x5002 sid: 911416-00789
2019-05-16 13:28:40,393 - servod - INFO - Press '1' for servo, vid: 0x18d1 pid: 0x5002 sid: 911416-00927
2019-05-16 13:28:40,396 - servod - INFO - Press '2' for servo, vid: 0x18d1 pid: 0x5014 sid: 0601002A-922A4826
2019-05-16 13:28:40,396 - servod - INFO - Press '3' for servo, vid: 0x18d1 pid: 0x501b sid: C1804020116
```

### Example

```bash
# servo v4
(chroot) $ sudo servod --board=nocturne  --port 9999 --serialname C1804020116

# servo v2
(chroot) $ sudo servod --board=zerblebarn  --serialname 911416-00789 --port 9998

# servo micro
(chroot) $ sudo servod --board=hatch --serialname CMO653-00166-040489J03624 --port 9997
```

*** note
NOTE: By default `dut-control` will use port 9999 (the default `servod` port).
You can specify the `--port` flag to `dut-control` to target a specific
`servod`:

```bash
(chroot)$ dut-control --port 9998 power_state:off
```
***


[FAFT]: https://www.chromium.org/for-testers/faft
[FAFT setup image]: https://www.chromium.org/for-testers/faft/Servo2_with_labels.jpg
[developer_guide]: https://chromium.googlesource.com/chromiumos/docs/+/master/developer_guide.md
[servo library code]: https://chromium.googlesource.com/chromiumos/third_party/autotest/+/master/server/cros/servo/
[Chromium OS autotest repo]: https://chromium.googlesource.com/chromiumos/third_party/autotest
[Servo v2]: ./servo_v2.md
[Servo v4]: ./servo_v4.md
[Servo Micro]: ./servo_micro.md
[servod_no_nspid]: https://groups.google.com/a/google.com/d/msg/chromeos-chatty-firmware/mDexO8T1TyM/rFONCSifAAAJ
[CCD]: https://chromium.googlesource.com/chromiumos/platform/ec/+/refs/heads/master/docs/case_closed_debugging_cr50.md
