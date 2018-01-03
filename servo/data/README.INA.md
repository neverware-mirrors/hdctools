# INA Configuration Files

## Overview

To measure power on a board, the power measurement sources (be it on-board ADCs,
or by using a sweetberry device) need to be properly configured.
They need to be given human-readable names, and told the sense resistor sizes in
addition to some other information.

This is a small introduction on how those configurations are generated, to
facilitate creating new configurations.

## File Format

Servo uses python to write human-readable INA configuration templates, that then
generate slightly-less-but-still human readable configuration files.

### Variables:
There are up to 3 variables inside the configuration file needed.

- **inas:** A list of tuples that describe which INAs to configure.
            Each tuple consists of

  (type, addr, name, nom, sense, location, calib)\*

    - **type**: one of ina3221, ina219, ina231 (for now all the supported types)
    - **addr**: i2c slave address
    - **name**: human readable name used to control measurements later
    - **sense**: sense resistor value in Ohm
    - **location**:
    - **calib**: True if the rail should be configured for power measurements
               (usually, this means r-sense is non zero)

  \* order matters since this is a tuple

- **config\_type(*optional*):** either 'servod' or 'sweetberry'

  If |config\_type| is **servod**, then a set of servod controls for each rail
  will be generated, in a servod .xml configuration file. This file then can be
  sourced when starting servod.
  *Use this configuration type for on-board INAs*.

  If |config\_type| is **sweetberry**, then a .board and .scenario configuration
  file for usage with powerlog.py will be generated.
  *Use this configuration type when creating a sweetberry config*.

  If |config\_type| is not defined, it will default to servod.

 - **revs *(optional)*:** A list of integers describing what hardware revisions
                          this configuration is valid for.

   These are used to generate configurations using a standard naming scheme
   (see below).

### File name conventions:

The filename of the .py configuration template should be board\_[suffix].py.

If |revs| (see above) is defined, then the output configuration files after
building hdctools will be named

**board\_rev\_[rev].[filetype]**

There will be identical configuration files one for each rev in |revs|.

If |revs| is not defined, then the output configuration file after building
hdctools will be named

**board\_[suffix].[filetype]**

- filetype is either .xml or .board/.scenario depending on the configuration
  being for sweetberry or servod
- rev being the revision numbers specified in the |revs| variable


So the [suffix] might matter in cases where no |revs| are defined, or it might
be thrown out, when |revs| are defined.


## Output Format

For more details, see generate\_ina\_controls.py

### sweetberry

For sweetberry, the output are a .board file that is a list of dictionaries,
where each dictionary defines the:

- INA name
- INA address
- sense resistor size

and a .scenario file that lists all the inas names again, so that powerlog.py
collects measurements from all of them. See powerlog.py for details.

### servod

For servod, the output is a .xml servod configuration file that defines servod
controls for:

- bus voltage
- shunt voltage
- current *(if calibration is True)*
- power *(if calibration is True)*
- config\_register
- calib\_register *(if available)*
