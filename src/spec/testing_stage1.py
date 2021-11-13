#!/usr/bin/env python3
from nmigen.build.dsl import Resource, Subsignal, Pins
from nmigen.build.plat import TemplatedPlatform
from nmigen import Elaboratable, Signal, Module

# Was thinking of using these functions, but skipped for simplicity for now
# XXX nope.  the output from JSON file.
#from pinfunctions import (i2s, lpc, emmc, sdmmc, mspi, mquadspi, spi,
# quadspi, i2c, mi2c, jtag, uart, uartfull, rgbttl, ulpi, rgmii, flexbus1,
# flexbus2, sdram1, sdram2, sdram3, vss, vdd, sys, eint, pwm, gpio)

# File for stage 1 pinmux tested proposed by Luke,
https://bugs.libre-soc.org/show_bug.cgi?id=50#c10


def dummy_pinset():
    # sigh this needs to come from pinmux.
    gpios = []
    for i in range(16):
        gpios.append("%d*" % i)
    return {'uart': ['tx+', 'rx-'],
            'gpio': gpios,
            'i2c': ['sda*', 'scl+']}

"""
a function is needed which turns the results of dummy_pinset()
into:

[UARTResource("uart", 0, tx=..., rx=..),
 I2CResource("i2c", 0, scl=..., sda=...),
 Resource("gpio", 0, Subsignal("i"...), Subsignal("o"...)
 Resource("gpio", 1, Subsignal("i"...), Subsignal("o"...)
 ...
]
"""


def create_resources(pinset):
    resources = []
    for periph, pins in pinset.items():
        print(periph, pins)
        if periph == 'i2c':
            #print("I2C required!")
            resources.append(I2CResource('i2c', 0, sda='sda', scl='scl'))
        elif periph == 'uart':
            #print("UART required!")
            resources.append(UARTResource('uart', 0, tx='tx', rx='rx'))
        elif periph == 'gpio':
            #print("GPIO required!")
            print ("GPIO is defined as '*' type, meaning i, o and oe needed")
            resources.append(Resource('gpio', 0,
              Subsignal("i", Pins('i0', dir="i", conn=None, assert_width=1)),
              Subsignal("oe", Pins('oe0', dir="o", conn=None, assert_width=1)),
              Subsignal("o", Pins('o0', dir="o", conn=None, assert_width=1))))
    return resources


def UARTResource(*args, rx, tx):
    io = []
    io.append(Subsignal("rx", Pins(rx, dir="i", assert_width=1)))
    io.append(Subsignal("tx", Pins(tx, dir="o", assert_width=1)))
    return Resource.family(*args, default_name="uart", ios=io)


def I2CResource(*args, scl, sda):
    io = []
    io.append(Subsignal("scl", Pins(scl, dir="io", assert_width=1)))
    io.append(Subsignal("sda", Pins(sda, dir="io", assert_width=1)))
    return Resource.family(*args, default_name="i2c", ios=io)


# ridiculously-simple top-level module.  doesn't even have a sync domain
# and can't have one until a clock has been established by DummyPlatform.
class Blinker(Elaboratable):
    def __init__(self):
        pass
    def elaborate(self, platform):
        m = Module()
        count = Signal(5)
        m.d.comb += count.eq(5)
        return m


# sigh, have to create a dummy platform for now.
# TODO: investigate how the heck to get it to output ilang. or verilog.
# or, anything, really.  but at least it doesn't barf
class DummyPlatform(TemplatedPlatform):
    resources = []
    connectors = []
    required_tools = []
    command_templates = ['/bin/true']
    file_templates = TemplatedPlatform.build_script_templates
    toolchain = None
    def __init__(self, resources):
        self.resources = resources
        super().__init__()

"""
and to create a Platform instance with that list, and build
something random

   p=Platform()
   p.resources=listofstuff
   p.build(Blinker())
"""
pinset = dummy_pinset()
resources = create_resources(pinset)
print(pinset)
print(resources)
p = DummyPlatform (resources)
p.resources = create_resources(pinset)
p.build(Blinker())

