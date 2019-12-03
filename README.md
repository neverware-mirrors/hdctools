# hdctools: Chrome OS Hardware Debug & Control Tools

This repository contains source code and documentation for the Servo debug
boards. The tools in this repository require the full [CrOS chroot][Developer
guide], while the [Standalone hdctools] can be used without the chroot.

[TOC]

## Servo

*   [Servo: Debug Board](./docs/servo.md)
    *   [Servo v2](./docs/servo_v2.md)
    *   [Servo v4](./docs/servo_v4.md)
    *   [Servo Micro](./docs/servo_micro.md)

## servod

*   [`servod`: Daemon for Servo](./docs/servod.md)
*   [`servod` FAQ](./docs/servod_faq.md)

## Closed Case Debugging (CCD)

*   [Closed Case Debugging (CCD) Overview](./docs/ccd.md)

## Power Measurement

*   [Power Measurement](./docs/power_measurement.md)
*   [Sweetberry Power Monitoring Board](./docs/sweetberry.md)
*   [INA: Instrumentation Amplifier](./docs/ina.md)

## Resources

*   [Standalone hdctools]: Run common hardware debug tasks outside the chroot.
*   [File a Bug](https://bugs.chromium.org/p/chromium/issues/entry?components=Tools%3EChromeOSDebugBoards)
*   [Contact](https://chromium.googlesource.com/chromiumos/docs/+/master/contact.md)

[Standalone hdctools]: https://chromium.googlesource.com/chromiumos/platform/standalone-hdctools
[Developer guide]: https://chromium.googlesource.com/chromiumos/docs/+/master/developer_guide.md
