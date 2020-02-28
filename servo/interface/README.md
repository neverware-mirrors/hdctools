# Introduction

A servo interface (effectively) maps to a usb end-point on a servo device that
can perform a certain task. More generally, the idea is that a servo device
supports multiple interfaces to perform multiple separate tasks. So far, we
support GPIO, I2C, and UART interfaces. This short README is designed to give an
overview of the servo.interface module.

# Overview

Recall that a servo device is one usb device with a collection of interfaces.
Depending on the device, there are different interfaces. These interfaces are
implemented in this module. The module itself provides a 'clean' discovery
method that allows the interface writers to identify their interface with a
'name' static method, and the servo\_interfaces.py list (that maps servo
devices to a list of interfaces and parameters on how to build them). So adding
a new interface happens here, while describing how to build and deploy that
interface on a new servo device happens in servo\_interfaces.py.

Lastly, consider an example like ec3po: this is an entirely software interface
that takes an underlying "real" interface and provide functionality on top of
that. This means that an interface can also be developed by adding functionality
on top of a current interface.

# defining Build()

Build is invoked from the servo\_server with keyword arguments only. It gets
invoked with the union of all arguments that any known Build implementation
needs. This means that some Build() implementations do not require the passed in
arguments. It's fine to either ignore them (and mark so for pylint) or leverage
|kwargs|.

In its current implemenation Build is invoked with the following parameters:
- index: the interface index i.e. whether it's the first, second, or 10th
- vid, pid, serial: the identifiers for the underlying device
- interface\_data: a (custom) dictionary with extra data to build the interface.
  This is taken directory from servo\_interfaces.py and passed to the Build()
  function.
- servod: a reference to servod for interfaces that need to query information
  about the system to build themselves e.g. ec3po
