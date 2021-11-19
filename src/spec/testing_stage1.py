#!/usr/bin/env python3
from nmigen.build.dsl import Resource, Subsignal, Pins
from nmigen.build.plat import TemplatedPlatform
from nmigen.build.res import ResourceManager, ResourceError
from nmigen import Elaboratable, Signal, Module, Instance
from collections import OrderedDict
from jtag import JTAG, resiotypes
from copy import deepcopy

# extra dependencies for jtag testing (?)
from soc.bus.sram import SRAM

from nmigen import Memory
from nmigen.sim import Simulator, Delay, Settle, Tick

from nmutil.util import wrap

from soc.debug.jtagutils import (jtag_read_write_reg,
                                 jtag_srv, jtag_set_reset,
                                 jtag_set_ir, jtag_set_get_dr)

from c4m.nmigen.jtag.tap import TAP, IOType
from c4m.nmigen.jtag.bus import Interface as JTAGInterface
from soc.debug.dmi import DMIInterface, DBGCore
from soc.debug.test.dmi_sim import dmi_sim
from soc.debug.test.jtagremote import JTAGServer, JTAGClient

# Was thinking of using these functions, but skipped for simplicity for now
# XXX nope.  the output from JSON file.
#from pinfunctions import (i2s, lpc, emmc, sdmmc, mspi, mquadspi, spi,
# quadspi, i2c, mi2c, jtag, uart, uartfull, rgbttl, ulpi, rgmii, flexbus1,
# flexbus2, sdram1, sdram2, sdram3, vss, vdd, sys, eint, pwm, gpio)

# File for stage 1 pinmux tested proposed by Luke,
# https://bugs.libre-soc.org/show_bug.cgi?id=50#c10


def dummy_pinset():
    # sigh this needs to come from pinmux.
    gpios = []
    for i in range(4):
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
            ios = []
            for pin in pins:
                pname = "gpio"+pin[:-1] # strip "*" on end
                # urrrr... tristsate and io assume a single pin which is
                # of course exactly what we don't want in an ASIC: we want
                # *all three* pins but the damn port is not outputted
                # as a triplet, it's a single Record named "io". sigh.
                # therefore the only way to get a triplet of i/o/oe
                # is to *actually* create explicit triple pins
                pad = Subsignal("io",
                            Pins("%s_i %s_o %s_oe" % (pname, pname, pname),
                                 dir="io", assert_width=3))
                ios.append(Resource(pname, 0, pad))
            resources.append(Resource.family(periph, 0, default_name="gpio",
                                             ios=ios))

    # add clock and reset
    clk = Resource("clk", 0, Pins("sys_clk", dir="i"))
    rst = Resource("rst", 0, Pins("sys_rst", dir="i"))
    resources.append(clk)
    resources.append(rst)
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
# and can't have one until a clock has been established by ASICPlatform.
class Blinker(Elaboratable):
    def __init__(self, pinset):
        self.jtag = JTAG({}, "sync")

    def elaborate(self, platform):
        m = Module()
        m.submodules.jtag = self.jtag
        count = Signal(5)
        m.d.sync += count.eq(5)
        print ("resources", platform.resources.items())
        gpio = platform.request('gpio')
        print (gpio, gpio.layout, gpio.fields)
        # get the GPIO bank, mess about with some of the pins
        m.d.comb += gpio.gpio0.io.o.eq(1)
        m.d.comb += gpio.gpio1.io.o.eq(gpio.gpio2.io.i)
        m.d.comb += gpio.gpio1.io.oe.eq(count[4])
        m.d.sync += count[0].eq(gpio.gpio1.io.i)
        # get the UART resource, mess with the output tx
        uart = platform.request('uart')
        print (uart, uart.fields)
        intermediary = Signal()
        m.d.comb += uart.tx.eq(intermediary)
        m.d.comb += intermediary.eq(uart.rx)
        return m


'''
    _trellis_command_templates = [
        r"""
        {{invoke_tool("yosys")}}
            {{quiet("-q")}}
            {{get_override("yosys_opts")|options}}
            -l {{name}}.rpt
            {{name}}.ys
        """,
    ]
'''

# sigh, have to create a dummy platform for now.
# TODO: investigate how the heck to get it to output ilang. or verilog.
# or, anything, really.  but at least it doesn't barf
class ASICPlatform(TemplatedPlatform):
    connectors = []
    resources = OrderedDict()
    required_tools = []
    command_templates = ['/bin/true']
    file_templates = {
        **TemplatedPlatform.build_script_templates,
        "{{name}}.il": r"""
            # {{autogenerated}}
            {{emit_rtlil()}}
        """,
        "{{name}}.debug.v": r"""
            /* {{autogenerated}} */
            {{emit_debug_verilog()}}
        """,
    }
    toolchain = None
    default_clk = "clk" # should be picked up / overridden by platform sys.clk
    default_rst = "rst" # should be picked up / overridden by platform sys.rst

    def __init__(self, resources, jtag):
        self.pad_mgr = ResourceManager([], [])
        self.jtag = jtag
        super().__init__()
        # create set of pin resources based on the pinset, this is for the core
        self.add_resources(resources)
        # record resource lookup between core IO names and pads
        self.padlookup = {}

    def request(self, name, number=0, *, dir=None, xdr=None):
        """request a Resource (e.g. name="uart", number=0) which will
        return a data structure containing Records of all the pins.

        this override will also - automatically - create a JTAG Boundary Scan
        connection *without* any change to the actual Platform.request() API
        """
        # okaaaay, bit of shenanigens going on: the important data structure
        # here is Resourcemanager._ports.  requests add to _ports, which is
        # what needs redirecting.  therefore what has to happen is to
        # capture the number of ports *before* the request. sigh.
        start_ports = len(self._ports)
        value = super().request(name, number, dir=dir, xdr=xdr)
        end_ports = len(self._ports)

        # now make a corresponding (duplicate) request to the pad manager
        # BUT, if it doesn't exist, don't sweat it: all it means is, the
        # application did not request Boundary Scan for that resource.
        pad_start_ports = len(self.pad_mgr._ports)
        try:
            pvalue = self.pad_mgr.request(name, number, dir=dir, xdr=xdr)
        except AssertionError:
            return value
        pad_end_ports = len(self.pad_mgr._ports)

        # ok now we have the lengths: now create a lookup between the pad
        # and the core, so that JTAG boundary scan can be inserted in between
        core = self._ports[start_ports:end_ports]
        pads = self.pad_mgr._ports[pad_start_ports:pad_end_ports]
        # oops if not the same numbers added. it's a duplicate. shouldn't happen
        assert len(core) == len(pads), "argh, resource manager error"
        print ("core", core)
        print ("pads", pads)

        # pad/core each return a list of tuples of (res, pin, port, attrs)
        for pad, core in zip(pads, core):
            # create a lookup on pin name to get at the hidden pad instance
            # this pin name will be handed to get_input, get_output etc.
            # and without the padlookup you can't find the (duplicate) pad.
            # note that self.padlookup and self.jtag.ios use the *exact* same
            # pin.name per pin
            pin = pad[1]
            corepin = core[1]
            if pin is None: continue # skip when pin is None
            assert corepin is not None # if pad was None, core should be too
            print ("iter", pad, pin.name)
            print ("existing pads", self.padlookup.keys())
            assert pin.name not in self.padlookup # no overwrites allowed!
            assert pin.name == corepin.name       # has to be the same!
            self.padlookup[pin.name] = pad        # store pad by pin name

            # now add the IO Shift Register.  first identify the type
            # then request a JTAG IOConn. we can't wire it up (yet) because
            # we don't have a Module() instance. doh. that comes in get_input
            # and get_output etc. etc.
            iotype = resiotypes[pin.dir] # look up the C4M-JTAG IOType
            io = self.jtag.add_io(iotype=iotype, name=pin.name) # create IOConn
            self.jtag.ios[pin.name] = io # store IOConn Record by pin name

        # finally return the value just like ResourceManager.request()
        return value

    def add_resources(self, resources, no_boundary_scan=False):
        super().add_resources(resources)
        if no_boundary_scan:
            return
        # make a *second* - identical - set of pin resources for the IO ring
        padres = deepcopy(resources)
        self.pad_mgr.add_resources(padres)

    #def iter_ports(self):
    #    yield from super().iter_ports()
    #    for io in self.jtag.ios.values():
    #        print ("iter ports", io.layout, io)
    #        for field in io.core.fields:
    #            yield getattr(io.core, field)
    #        for field in io.pad.fields:
    #            yield getattr(io.pad, field)

    # XXX these aren't strictly necessary right now but the next
    # phase is to add JTAG Boundary Scan so it maaay be worth adding?
    # at least for the print statements
    def get_input(self, pin, port, attrs, invert):
        self._check_feature("single-ended input", pin, attrs,
                            valid_xdrs=(0,), valid_attrs=None)

        m = Module()
        print ("    get_input", pin, "port", port, port.layout)
        if pin.name in ['clk_0', 'rst_0']: # sigh
            # simple pass-through from port to pin
            print("No JTAG chain in-between")
            m.d.comb += pin.i.eq(self._invert_if(invert, port))
            return m
        (padres, padpin, padport, padattrs) = self.padlookup[pin.name]
        io = self.jtag.ios[pin.name]
        print ("       pad", padres, padpin, padport, attrs)
        print ("       padpin", padpin.layout)
        print ("      jtag", io.core.layout, io.pad.layout)
        m.d.comb += pin.i.eq(self._invert_if(invert, port))
        m.d.comb += padpin.i.eq(padport)
        m.d.comb += padport.io.eq(io.core.i)
        m.d.comb += io.pad.i.eq(pin.i)

        print("+=+=+= pin: ", pin)
        print("+=+=+= port: ", port.layout)
        print("+=+=+= pad pin: ", padpin)
        print("+=+=+= pad port: ", padport)
        return m

    def get_output(self, pin, port, attrs, invert):
        self._check_feature("single-ended output", pin, attrs,
                            valid_xdrs=(0,), valid_attrs=None)

        m = Module()
        print ("    get_output", pin, "port", port, port.layout)
        if pin.name in ['clk_0', 'rst_0']: # sigh
            # simple pass-through from pin to port
            print("No JTAG chain in-between")
            m.d.comb += port.eq(self._invert_if(invert, pin.o))
            return m
        (padres, padpin, padport, padattrs) = self.padlookup[pin.name]
        io = self.jtag.ios[pin.name]
        print ("       pad", padres, padpin, padport, padattrs)
        print ("       pin", padpin.layout)
        print ("      jtag", io.core.layout, io.pad.layout)
        m.d.comb += port.eq(self._invert_if(invert, pin.o))
        m.d.comb += padport.io.eq(self._invert_if(invert, padpin.o))
        m.d.comb += io.core.o.eq(port.io)
        m.d.comb += padpin.o.eq(io.pad.o)
        return m

    def get_tristate(self, pin, port, attrs, invert):
        self._check_feature("single-ended tristate", pin, attrs,
                            valid_xdrs=(0,), valid_attrs=None)

        print ("    get_tristate", pin, "port", port, port.layout)
        m = Module()
        if pin.name in ['clk_0', 'rst_0']: # sigh
            print("No JTAG chain in-between")
            m.submodules += Instance("$tribuf",
                p_WIDTH=pin.width,
                i_EN=pin.oe,
                i_A=self._invert_if(invert, pin.o),
                o_Y=port,
            )
            return m
        (res, pin, port, attrs) = self.padlookup[pin.name]
        io = self.jtag.ios[pin.name]
        print ("       pad", res, pin, port, attrs)
        print ("       pin", pin.layout)
        print ("      jtag", io.core.layout, io.pad.layout)
        #m.submodules += Instance("$tribuf",
        #    p_WIDTH=pin.width,
        #    i_EN=io.pad.oe,
        #    i_A=self._invert_if(invert, io.pad.o),
        #    o_Y=port,
        #)
        m.d.comb += io.core.o.eq(pin.o)
        m.d.comb += io.core.oe.eq(pin.oe)
        m.d.comb += pin.i.eq(io.core.i)
        m.d.comb += io.pad.i.eq(port.i)
        m.d.comb += port.o.eq(io.pad.o)
        m.d.comb += port.oe.eq(io.pad.oe)
        return m

    def get_input_output(self, pin, port, attrs, invert):
        self._check_feature("single-ended input/output", pin, attrs,
                            valid_xdrs=(0,), valid_attrs=None)
        
        print ("    get_input_output", pin, "port", port, port.layout)
        m = Module()    
        if pin.name in ['clk_0', 'rst_0']: # sigh
            print("No JTAG chain in-between")
            m.submodules += Instance("$tribuf",
                p_WIDTH=pin.width,
                i_EN=pin.oe,
                i_A=self._invert_if(invert, pin.o),
                o_Y=port,
            )
            m.d.comb += pin.i.eq(self._invert_if(invert, port))
            return m
        (padres, padpin, padport, padattrs) = self.padlookup[pin.name]
        io = self.jtag.ios[pin.name]
        print ("       pad", padres, padpin, padport, padattrs)
        print ("       pin", padpin.layout)
        print ("       port layout", port.layout)
        print ("      jtag", io.core.layout, io.pad.layout)
        #m.submodules += Instance("$tribuf",
        #    p_WIDTH=pin.width,
        #    i_EN=io.pad.oe,
        #    i_A=self._invert_if(invert, io.pad.o),
        #    o_Y=port,
        #)
        # Create aliases for the port sub-signals
        port_i = port.io[0]
        port_o = port.io[1]
        port_oe = port.io[2]
        
        padport_i = padport.io[0]
        padport_o = padport.io[1]
        padport_oe = padport.io[2]

        # Connect SoC pins to SoC port
        m.d.comb += pin.i.eq(port_i)
        m.d.comb += port_o.eq(pin.o)
        m.d.comb += port_oe.eq(pin.oe)
        # Connect SoC port to JTAG io.core side 
        m.d.comb += port_i.eq(io.core.i)
        m.d.comb += io.core.o.eq(port_o)
        m.d.comb += io.core.oe.eq(port_oe)
        # Connect JTAG io.pad side to pad port
        m.d.comb += io.pad.i.eq(padport_i)
        m.d.comb += padport_o.eq(io.pad.o)
        m.d.comb += padport_oe.eq(io.pad.oe)
        # Connect pad port to pad pins
        m.d.comb += padport_i.eq(padpin.i)
        m.d.comb += padpin.o.eq(padport_o)
        m.d.comb += padpin.oe.eq(padport_oe)
        return m


"""
and to create a Platform instance with that list, and build
something random

   p=Platform()
   p.resources=listofstuff
   p.build(Blinker())
"""
pinset = dummy_pinset()
top = Blinker(pinset)
print(pinset)
resources = create_resources(pinset)
p = ASICPlatform (resources, top.jtag)
p.build(top)

# dut = JTAG(test_pinset(), wb_data_wid=64, domain="sync")
top.jtag.stop = False
# rather than the client access the JTAG bus directly
# create an alternative that the client sets
class Dummy: pass
cdut = Dummy()
cdut.cbus = JTAGInterface()

# set up client-server on port 44843-something
top.jtag.s = JTAGServer()
cdut.c = JTAGClient()
top.jtag.s.get_connection()
#else:
#    print ("running server only as requested, use openocd remote to test")
#    sys.stdout.flush()
#    top.jtag.s.get_connection(None) # block waiting for connection

# take copy of ir_width and scan_len
cdut._ir_width = top.jtag._ir_width
cdut.scan_len = top.jtag.scan_len

memory = Memory(width=64, depth=16)
sram = SRAM(memory=memory, bus=top.jtag.wb)

#m = Module()
#m.submodules.ast = dut
#m.submodules.sram = sram

sim = Simulator(top)
sim.add_clock(1e-6, domain="sync")      # standard clock

sim.add_sync_process(wrap(jtag_srv(top))) #? jtag server
#if len(sys.argv) != 2 or sys.argv[1] != 'server':
sim.add_sync_process(wrap(jtag_sim(cdut, top.jtag))) # actual jtag tester
sim.add_sync_process(wrap(dmi_sim(top.jtag)))  # handles (pretends to be) DMI

with sim.write_vcd("dmi2jtag_test_srv.vcd"):
    sim.run()
