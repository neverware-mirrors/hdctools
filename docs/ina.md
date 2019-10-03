# INA Configuration Files

[TOC]

## Overview

To measure power on a board, the power measurement sources (be it on-board ADCs,
or by using a sweetberry device) need to be properly configured. They need to be
given human-readable names, and told the sense resistor sizes in addition to
some other information.

This is a small introduction on how those configurations are generated, to
facilitate creating new configurations.

## File Format

Servo uses python to write human-readable INA configuration templates, that then
generate slightly-less-but-still human readable configuration files.

### Variables

There are up to 3 variables inside the configuration file needed.

*   **`inas`:** A list of tuples that describe which INAs to configure. Each
    tuple consists of

    `(type, addr, name, nom, sense, location, calib)`\*

    *   **`type`**: one of `ina3221`, `ina219`, `ina231`, `sweetberry`
    *   **`addr`**: i2c slave address (see sweetberry below for note)
    *   **`name`**: human readable name used to control measurements later
    *   **`nom`**: nominal voltage of power rail
    *   **`sense`**: sense resistor value in Ohm
    *   **`location`**: loc string for docstring generation
    *   **`calib`**: `True` if the rail should be configured for power
        measurements (usually, this means r-sense is non zero)

    \* order matters since this is a tuple

*   **`config_type`(*optional*):** either `servod` or `sweetberry`

    If `config_type` is **`servod`**, then a set of `servod` controls for each
    rail will be generated, in a `servod` `.xml` configuration file. This file
    then can be sourced when starting servod. *Use this configuration type for
    on-board INAs*.

    If `config_type` is **`sweetberry`**, a set of servod controls for each rail
    will be generated, similar to the `servod` config, but specifically to use
    sweetberry through `servod`. Additionally, a `.board` and `.scenario`
    configuration file for usage with `powerlog.py` will be generated. See below
    for sweetberry details. *Use this configuration type when creating a
    sweetberry config*.

    If `config_type` is not defined, it will default to `servod`.

*   **`revs` *(optional)*:** A list of integers describing what hardware
    revisions this configuration is valid for.

    These are used to generate configurations using a standard naming scheme
    (see below).

### File name conventions

The filename of the `.py` configuration template should be `board_[suffix].py`.

If `revs` (see above) is defined, then the output configuration files after
building `hdctools` will be named

**`board_rev[rev].[filetype]`**

*   `filetype` is either `.xml` or `.board`/`.scenario` depending on the
    configuration being for `servod` or `powerlog` usage.
*   `rev` being the revision numbers specified in the `revs` variable
*   `rev[rev]` also matches the output from `mosys platform version` in AP
    console

Each `rev` in `revs` produces the same configuration. For example if `revs =
[0,1]` then the ina generation will create `board_rev0.[filetype]` -
`board_rev1.[filetype]`.

If `revs` is not defined, then the output configuration file after building
`hdctools` will be named identical to its `.py` template:

**`board_[suffix].[filetype]`**

The `suffix` matters in cases where no `revs` are defined, and it will be thrown
out, when `revs` are defined.

## Output Format

For more details, see `generate_ina_controls.py`.

### sweetberry

The output is a `servod`-style `.xml` control file, where the driver is
"sweetberry" as a wrapper around the `ina231.py` driver, and a powerlog config
file pair (`.board` and `.scenario` files). See below at `servod` for the
controls exposed by the `.xml` file.

Sweetberry is not trivial to manually configure properly with i2c slave address
and the i2c port. This is due to each physical bank using multiple ports, and a
slave address subset. To facilitate this, on `config_type='sweetberry'` one can
write the `.py` template also by setting:

*   the slv-addr slot to a tuple containing both the pins (e.g. `(1,3))`
*   the loc variable slot to the `j` bank: `j2,j3,j4` (see marks on board)

To summarize here are two equivalent rail configurations:

```python
('sweetberry', (1,3), 'sample_rail_mw' , 5.0, 0.010, 'j2', False)

('sweetberry', '0x40:3', 'sample_rail_mw' , 5.0, 0.010, 'j2', False)
```

as the first line will be converted into the 2nd line in preprocessing. Same
below.

```python
('sweetberry', (1,3), 'sample_rail_mw' , 5.0, 0.010, 'j3', False)

('sweetberry', '0x44:3', 'sample_rail_mw' , 5.0, 0.010, 'j3', False)
```

See [sweetberry] for the details on banks, ports, and i2c addresses.

See `servo_sweetberry_rails.py` for a full list of sweetberry controls using the
i2c address space.

See `servo_sweetberry_rails_pins.py` for a full list of sweetberry controls
using the pin + jbank address space.

The `.board` file that is a list of dictionaries, where each dictionary defines:

*   INA name
*   INA address
*   sense resistor size
*   INA i2c address
*   INA i2c port

and a `.scenario` file that lists all the inas names again, so that
[powerlog.py] collects measurements from all of them. See [powerlog.py] for
details.

### servod

For `servod`, the output is a `.xml` `servod` configuration file that defines
`servod` controls for:

*   bus voltage
*   shunt voltage
*   current *(if calibration is True)*
*   power *(if calibration is True)*
*   `config_register`
*   `calib_register` *(if available)*

[powerlog.py]:https://chromium.googlesource.com/chromiumos/platform/ec/+/refs/heads/master/extra/usb_power/board.README
[sweetberry]: ./sweetberry.md
