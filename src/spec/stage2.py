#!/usr/bin/env python3
"""
pinmux documented here https://libre-soc.org/docs/pinmux/
"""
from nmigen.build.dsl import Resource, Subsignal, Pins
from nmigen.build.plat import TemplatedPlatform
from nmigen.build.res import ResourceManager, ResourceError
from nmigen.hdl.rec import Layout
from nmigen import Elaboratable, Signal, Module, Instance
from collections import OrderedDict
from jtag import JTAG, resiotypes, iotypes, scanlens
from copy import deepcopy
from nmigen.cli import rtlil
import sys

# extra dependencies for jtag testing (?)
#from soc.bus.sram import SRAM

#from nmigen import Memory
from nmigen.sim import Simulator, Delay, Settle, Tick, Passive

from nmutil.util import wrap

from nmutil.gtkw import write_gtkw

# from soc.debug.jtagutils import (jtag_read_write_reg,
#                                 jtag_srv, jtag_set_reset,
#                                 jtag_set_ir, jtag_set_get_dr)

from soc.debug.test.test_jtag_tap import (jtag_read_write_reg,
                                          jtag_set_reset,
                                          jtag_set_shift_ir,
                                          jtag_set_shift_dr,
                                          jtag_set_run,
                                          jtag_set_idle,
                                          tms_data_getset)

def dummy_pinset():
    # sigh this needs to come from pinmux.
    gpios = []
    for i in range(4):
        gpios.append("%d*0" % i) # gpios to mux 0
    return {'uart': ['tx+1', 'rx-1'],
            'gpio': gpios,
            # 'jtag': ['tms-', 'tdi-', 'tdo+', 'tck+'],
            'i2c': ['sda*2', 'scl+2']}


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
# TODO: move to suitable location
class Pins:
    """declare a list of pins, including name and direction.  grouped by fn
    the pin dictionary needs to be in a reliable order so that the JTAG
    Boundary Scan is also in a reliable order
    """
    def __init__(self, pindict=None):
        if pindict is None:
            pindict = {}
        self.io_names = OrderedDict()
        if isinstance(pindict, OrderedDict):
            self.io_names.update(pindict)
        else:
            keys = list(pindict.keys())
            keys.sort()
            for k in keys:
                self.io_names[k] = pindict[k]

    def __iter__(self):
        # start parsing io_names and enumerate them to return pin specs
        scan_idx = 0
        for fn, pins in self.io_names.items():
            for pin in pins:
                # decode the pin name and determine the c4m jtag io type
                name, pin_type, bank = pin[:-2], pin[-2], pin[-1]
                iotype = iotypes[pin_type]
                pin_name = "%s_%s" % (fn, name)
                yield (fn, name, iotype, pin_name, scan_idx, bank)
                scan_idx += scanlens[iotype] # inc boundary reg scan offset


if __name__ == '__main__':
    #pname = "test"
    pinset = dummy_pinset()
    #print()
    #pin_test = Pins(Pins(pname+"_oe", dir="o", assert_width=1))
    pin_test = Pins(pinset)
    print(dir(pin_test))
    print(pin_test.io_names)
    for fn, name, iotype, pin_name, scan_idx, bank in pin_test:
        print(fn, name, iotype, pin_name, scan_idx, "Bank %s" % bank)
