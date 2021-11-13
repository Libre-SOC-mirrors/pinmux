#!/usr/bin/env python
from nmigen.build.dsl import Resource, Subsignal, Pins
from nmigen.build.plat import Platform # Not sure where platform comes from?

# Was thinking of using these functions, but skipped for simplicity for now
#from pinfunctions import i2s, lpc, emmc, sdmmc, mspi, mquadspi, spi, quadspi, i2c, mi2c, jtag, uart, uartfull, rgbttl, ulpi, rgmii, flexbus1, flexbus2, sdram1, sdram2, sdram3, vss, vdd, sys, eint, pwm, gpio

# File for stage 1 pinmux tested proposed by Luke, https://bugs.libre-soc.org/show_bug.cgi?id=50#c10

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
            resources.append(I2CResource('i2c', 0, sda='sda0', scl='scl0')) 
        elif periph == 'uart':
            #print("UART required!")
            resources.append(UARTResource('uart', 0, tx='tx0', rx='rx0'))
        elif periph == 'gpio':
            #print("GPIO required!")
            resources.append(Resource('gpio', 0, Subsignal("i", Pins('i0', dir="i", conn=None, assert_width=1)), Subsignal("o", Pins('o0', dir="o", conn=None, assert_width=1))))
    return resources

def UARTResource(*args, rx, tx, rts=None, cts=None, dtr=None, dsr=None, dcd=None, ri=None, 
                 conn=None, attrs=None, role=None):  
    io = []
    io.append(Subsignal("rx", Pins(rx, dir="i", conn=conn, assert_width=1)))
    io.append(Subsignal("tx", Pins(tx, dir="o", conn=conn, assert_width=1)))
    if attrs is not None:
        io.append(attrs)
    return Resource.family(*args, default_name="uart", ios=io)

def I2CResource(*args, scl, sda, conn=None, attrs=None):
    io = []
    io.append(Subsignal("scl", Pins(scl, dir="io", conn=conn, assert_width=1)))
    io.append(Subsignal("sda", Pins(sda, dir="io", conn=conn, assert_width=1)))
    if attrs is not None:
        io.append(attrs)
    return Resource.family(*args, default_name="i2c", ios=io)


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
p=Platform(resources)
p.resources = create_resources(pinset)
p.build(Blinker())

