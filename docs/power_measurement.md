# Chrome OS Power Measurement

This document details how developers can use hardware tools like Servo and
Sweetberry and software tools within [`dev-util/hdctools`][8] and other repos to
measure power on a Chrome OS device (DUT, device under test).

[TOC]

## Hardware to measure power

### Servo

Servo-like devices, including Servo V2, Servo V4, Micro Servo and Suzy-Qable,
can be used to measure power on the DUT with Analog-to-Digital Converters (ADCs)
on the board. For simplicity, this doc refers to them as just "Servo" devices.

See [Servo][5] for more information on Servo.

### Sweetberry

Sweetberry, Servo V1, or Servo INA adapter can be used when there are no ADCs on
the DUT. Sweetberry is the preferred method. A hardware rework on the DUT is
often required to place sense resistors on the power rails and to attach 'Medusa
style' header (HIROSE DF13A-40DP-1.25V(55)) to the sense resistors and ground.

See [Sweetberry Configuration][6] for more information on Sweetberry.

## Bridging hardware and software

### Create configuration file

Servo and Sweetberry can measure power on the DUT, but they have no awareness of
what power rails are being measured, or what size the sense resistors are.
Therefore, a configuration file is necessary to provide information about the
hardware setup. This configuration file is usually manually created by an
engineer and is fed into the power measurement software tool later.

File format: `.py`

See [INA Configuration Files][1] for instructions on how to write the
configuration file.

There are some slight differences between configuration files for Servo and that
for Sweetberry. See [this example][2] for configuration for Servo.

There are two ways to write Sweetberry configuration files. See
[`servo_sweetberry_rails_addr.py`][3] and [`servo_sweetberry_rails_pins.py`][4].

### Generate configuration file for software tool

The `.py` files created in the previous part need to be compiled into formats
required by the software tool.

If you created or edited the `.py` configuration file, first you need to run:

```bash
(chroot) $ cros_workon --host start dev-util/hdctools
```

This only needs to be run ONCE.

Then, every time after you edit the `.py` configuration file, run:

```bash
(chroot) $ sudo emerge dev-util/hdctools
```

To verify that you have generated configuration files successfully, look into
this directory:

```bash
(chroot) $ /usr/lib64/python2.7/site-packages/servo/data/
```

File format: `.xml` for servod, `.board` and `.scenario` for powerlog.

## Software tool to measure power

Start a servod instance in chroot to talk to the Servo or Sweetberry that is
attached to the DUT:

```bash
(chroot) $ sudo servod --board $BOARD --config $CONFIG_FILE.xml
```

Note that `$CONFIG_FILE.xml` is generated in the previous step. Both `dut-power`
and `dut-control` are servod clients that talk to servod and fetch power data
from the Servo or Sweetberry.

### dut-power

Recommended, for users who only want measurements in power.

```bash
(chroot) $ dut-power [arguments]
```

`dut-power` queries the selected servod to read power measurements from the
Servo or Sweetberry. See `dut-power -h` for setting arguments. `dut-power` works
with both Servo and Sweetberry. It packs configuring the ADCs, reading data,
calculating statistics, and saving to file into one command.

### dut-control

For power users, provides more info than power.

`dut-control` can collect power measurements from both EC and on-board ADCs.

#### EC

`dut-control` can query battery power via EC’s connection (I2C) to the battery,
namely `ppvar_vbat`. On newer devices, same data averaged over 1 minute can be
queried by `avg_ppvar_vbat`.

#### On-board ADCs

`dut-control` can query power rails specified in the configuration file.

#### Types of information

`dut-control` can query power, bus voltage and current for all rails above, and
additionally shunt voltage for on-board ADCs.

#### Configure the ADCs

The on-board ADCs can be configured to more accurately measure power depending
on the size of the sense resistors and shunt voltage across the sense resistors.
Choose from the follow quick configs:

Config                    | Context
------------------------- | ---------------------------------------
`regular_power`           | S0 measurements
`regular_power_no_hw_avg` | S0 measurements w/out avg (for debug)
`low_power`               | < S0 measurements
`low_power_no_hw_avg`     | < S0 measurements w/out avg (for debug)

#### Examples

1.  Create helper variable, without `ppvar_vbat`.

    ```bash
    (chroot) $ mv=$(dut-control bus_voltage_rails | cut -f 2 -d: | tr -d ',')
    (chroot) $ ma=$(dut-control current_rails | cut -f 2 -d: | tr -d ',')
    (chroot) $ mw=$(dut-control power_rails | cut -f 2 -d: | tr -d ',')
    (chroot) $ cfg_reg=$(echo $mv | sed 's/_mv/_cfg_reg/g')
    ```

2.  Configure on-board ADCs (everytime after running `servod`).

    ```bash
    (chroot) $ for cfg in $cfg_reg ; do dut-control $cfg:regular_power $cfg; done
    ```

    Or

    ```bash
    (chroot) $ for cfg in $cfg_reg ; do dut-control $cfg:low_power $cfg; done
    ```

3.  Measure each power rail once.

    ```bash
    (chroot) $ dut-control $mv
    (chroot) $ dut-control $ma
    (chroot) $ dut-control $mw
    ```

    And

    ```bash
    (chroot) $ dut-control avg_ppvar_vbat_mw
    (chroot) $ dut-control avg_ppvar_vbat_ma
    (chroot) $ dut-control avg_ppvar_vbat_mw
    ```

    Or

    ```bash
    (chroot) $ dut-control ppvar_vbat_mv
    (chroot) $ dut-control ppvar_vbat_ma
    (chroot) $ dut-control ppvar_vbat_mw
    ```

4.  Measure power for 1 second 30 times.

    ```bash
    (chroot) $ dut-control -t 30 -z 1000 $mw | grep @@ | cut -b 6-
    ```

### powerlog

See [Sweetberry USB power monitoring][7].

[1]: ./ina.md
[2]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/master/servo/data/nami_rev1_inas.py
[3]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/master/servo/data/servo_sweetberry_rails_addr.py
[4]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/master/servo/data/servo_sweetberry_rails_pins.py
[5]: ./servo.md
[6]: ./sweetberry.md
[7]: https://chromium.googlesource.com/chromiumos/platform/ec/+/master/extra/usb_power/powerlog.README.md
[8]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/master
