# Servod FAQ

[TOC]

## How do I turn off servod?

### tl;dr:

*   `servodutil -p $PORT stop`
*   `<unplug the servo device>`
*   `<Ctrl-C>` also works

### the longer read

There are currently two mechanisms to help with `servod` management:
[ServoScratch (through servodutil)][5] and [ServoDeviceWatchdog][6].

ServoScratch leaves information about each servod instance around (e.g. port,
pid). This information can be used to turn off servod.

ServoDeviceWatchdog regularly polls to ensure all devices (i.e. servos) that the
system started with are still attached. If not, it will gracefully terminate
servod.

## Where is the code logic for the control `control`?

### tl;dr:

Look for the control name in `data/` to see its configuration. Look for the
python module inside `drv/` named the same as the controls `drv` param. In there
look for either `set()`/`get()` method, or if `subtype` defined in params for
`_Set_|subtype|`/`_Get_|subtype|`.

### the longer read

As you might have read in the [`servod` docs], servo control routing uses the
`drv` and `cmd` and `subtype` arguments inside a control's params to determine
where to look for the control.

The `drv` param describes what python module from the `drv/` directory houses
the controls `drv` class. The class name is obtained by converting the `drv`
name into [camel case][1].

If no subtype is defined then the `drv` class' (or a parent class') `get()` or
`set()` method will be invoked.

If a subtype is defined, then a method called `_Get_|subtype|` or
`_Set_|subtype|` will be called.

The `cmd` param in params defines if a param is set or get. If it is missing,
then the params will be used for both set and get.

## What is the interface object passed into these drivers?

### tl;dr:

It's a servo_interface or the Servod instance (if `interface=="servo"`). The
control's config defines what interface to use. That number is the index into
the `servo_interfaces.py` interface list for the servo device you're using (v2,
micro, ccd, etc).

Common interfaces are:

*   `2`: DUT i2c for INAs
*   `8`: AP console
*   `9`: cr50 console
*   `10`: EC console

## How do I reroute/overwrite a control for a board?

### tl;dr:

If you want control `control_name` to route to `real_control_name` for a
specific board or servo device, you can create a control with a `<remap>` tag
which will remap the control defined in the tag to the control defined in the
name.

Example:

```xml
<control>
  <name>real_control_name</name>
  <doc>using real_control_name for control_name</doc>
  <remap>control_name</remap>
</control>
```

This ensures that whenever `control_name` is called, `real_control_name` gets
executed.

If you want to overwrite `control_name` for a board, just write a control named
the same in the board overlay and make sure that [clobber_ok=""][4] inside its
params. This ensures it will clobber a previous definition of the control if it
exists.

Board overlays are some of the last configs to be pulled in, so you redefine
there.

## How do I add a new control?

### tl;dr:

Add your control to the an existing configuration file in `data/` or create a
new one. Use an existing driver in `drv/` or create a new one. In your control
be sure to set `drv` and `subtype` so that the method and driver you intend to
call get called.

### the longer read

Reading the [`servod` docs] will help a lot with this.

Adding a new control involves adding a new configuration outlining what the
control does and adding driver support to execute the control.

The first decision to make is if the new functionality should extend an existing
configuration or not. Creating a new configuration means having to ensure it's
included in all the right places, which might be more appropiate for niche
controls.

The next decision to make is whether to extend an existing driver, or implement
a new driver. When implementing a new driver, ensure that its added to
`drv/__init__.py` as otherwise servod won't be able to find it.

Once a driver with the appropiate method and the control exist, you can test out
how you want to manage information. Hard-coding aspects into the driver makes
configuration files simpler as the params attribute needs fewer entries. However
it makes the driver less flexible, as that control's params now cannot be
overwritten on a per-board/servo device basis.

## How do I share data between methods in a driver?

### tl;dr:

Use class variables and dictionaries inside your driver to ensure that data can
be shared between different methods.

### the longer read

As you might have read in the [`servod` docs] each `servod` control gets its own
instance of the driver class, with its parameters passed to that instance's
constructor. So in order to share data across methods (to cache results, or
build out more complex functionality) the simplest way is to use class variables
inside the driver to share the information.

Keep in mind that while class variables in python are accessible through
`self.varname`, assigning anything new to `self.varname` does not assign to the
class variable but rather creates a new instance variable that masks the class
variable. Either explictly call the class variable, or use a mutable object as
your class variable (`list`, `dict`).

## How do I get started with servo scripting/automation?

### tl;dr:

You can either `import servo.client` if `hdctools` is installed when executing
these automations (a moblab, a chroot etc) and then just use the `Sclient` class
to create a proxy and send controls/use servod. [Example code using sclient][2].

Alternatively, you can create your own XMLRPC proxy and execute the exposed rpc
functions (the `Servod` class' methods) through that proxy.
[Example code using proxy][3].

[1]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/master/servo/servo_server.py#519
[2]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/master/servo/dut_control.py#354
[3]: https://chromium.googlesource.com/chromiumos/third_party/autotest/+/master/server/hosts/servo_host.py#177
[4]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/master/servo/system_config.py#134
[5]: ./servod.md#servod-util
[6]: ./servod.md#servo-device-watchdog
[`servod` docs]: ./servod.md
