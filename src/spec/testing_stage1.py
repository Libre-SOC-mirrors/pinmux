#!/usr/bin/env python3
from nmigen.build.dsl import Resource, Subsignal, Pins
from nmigen.build.plat import TemplatedPlatform
from nmigen.build.res import ResourceManager, ResourceError
from nmigen.hdl.rec import Layout
from nmigen import Elaboratable, Signal, Module, Instance
from collections import OrderedDict
from jtag import JTAG, resiotypes
from copy import deepcopy
from nmigen.cli import rtlil
import sys

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
from nmigen.build.res import ResourceError

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
            #'jtag': ['tms-', 'tdi-', 'tdo+', 'tck+'],
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
                # XXX ARRRGH, doesn't work
                #pad = Subsignal("io",
                #            Pins("%s_i %s_o %s_oe" % (pname, pname, pname),
                #                 dir="io", assert_width=3))
                #ios.append(Resource(pname, 0, pad))
                pads = []
                pads.append(Subsignal("i",
                            Pins(pname+"_i", dir="i", assert_width=1)))
                pads.append(Subsignal("o",
                            Pins(pname+"_o", dir="o", assert_width=1)))
                pads.append(Subsignal("oe",
                            Pins(pname+"_oe", dir="o", assert_width=1)))
                ios.append(Resource.family(pname, 0, default_name=pname,
                                                 ios=pads))
            resources.append(Resource.family(periph, 0, default_name="gpio",
                                             ios=ios))

    # add clock and reset
    clk = Resource("clk", 0, Pins("sys_clk", dir="i"))
    rst = Resource("rst", 0, Pins("sys_rst", dir="i"))
    resources.append(clk)
    resources.append(rst)
    return resources


def JTAGResource(*args):
    io = []
    io.append(Subsignal("tms", Pins("tms", dir="i", assert_width=1)))
    io.append(Subsignal("tdi", Pins("tdi", dir="i", assert_width=1)))
    io.append(Subsignal("tck", Pins("tck", dir="i", assert_width=1)))
    io.append(Subsignal("tdo", Pins("tdo", dir="o", assert_width=1)))
    return Resource.family(*args, default_name="jtag", ios=io)

def UARTResource(*args, rx, tx):
    io = []
    io.append(Subsignal("rx", Pins(rx, dir="i", assert_width=1)))
    io.append(Subsignal("tx", Pins(tx, dir="o", assert_width=1)))
    return Resource.family(*args, default_name="uart", ios=io)


def I2CResource(*args, scl, sda):
    ios = []
    pads = []
    pads.append(Subsignal("i", Pins(sda+"_i", dir="i", assert_width=1)))
    pads.append(Subsignal("o", Pins(sda+"_o", dir="o", assert_width=1)))
    pads.append(Subsignal("oe", Pins(sda+"_oe", dir="o", assert_width=1)))
    ios.append(Resource.family(sda, 0, default_name=sda, ios=pads))
    pads = []
    pads.append(Subsignal("i", Pins(scl+"_i", dir="i", assert_width=1)))
    pads.append(Subsignal("o", Pins(scl+"_o", dir="o", assert_width=1)))
    pads.append(Subsignal("oe", Pins(scl+"_oe", dir="o", assert_width=1)))
    ios.append(Resource.family(scl, 0, default_name=scl, ios=pads))
    return Resource.family(*args, default_name="i2c", ios=ios)


def recurse_down(asicpad, jtagpad):
    """recurse_down: messy ASIC-to-JTAG pad matcher which expects
    at some point some Records named i, o and oe, and wires them
    up in the right direction according to those names.  "i" for
    input must come *from* the ASIC pad and connect *to* the JTAG pad
    """
    eqs = []
    for asiclayout, jtaglayout in zip(asicpad.layout, jtagpad.layout):
        apad = getattr(asicpad, asiclayout[0])
        jpad = getattr(jtagpad, jtaglayout[0])
        print ("recurse_down", asiclayout, jtaglayout, apad, jpad)
        if isinstance(asiclayout[1], Layout):
            eqs += recurse_down(apad, jpad)
        elif asiclayout[0] == 'i':
            eqs.append(jpad.eq(apad))
        elif asiclayout[0] in ['o', 'oe']:
            eqs.append(apad.eq(jpad))
    return eqs


# top-level demo module.
class Blinker(Elaboratable):
    def __init__(self, pinset, resources):
        self.jtag = JTAG({}, "sync")
        self.jtag.pad_mgr = ResourceManager([], [])
        self.jtag.core_mgr = ResourceManager([], [])
        self.jtag.pad_mgr.add_resources(resources)
        self.jtag.core_mgr.add_resources(resources)
        # record resource lookup between core IO names and pads
        self.jtag.padlookup = {}
        self.jtag.requests_made = []
        self.jtag.boundary_scan_pads = []
        self.jtag.resource_table = {}
        self.jtag.resource_table_pads = {}
        self.jtag.eqs = []
        memory = Memory(width=32, depth=16)
        self.sram = SRAM(memory=memory, bus=self.jtag.wb)

        # allocate all resources in advance in pad/core ResourceManagers
        for resource in resources:
            print ("JTAG resource", resource)
            if resource.name in ['clk', 'rst']: # hack
                continue
            self.add_jtag_request(resource.name, resource.number)

    def elaborate(self, platform):
        jtag_resources = self.jtag.pad_mgr.resources
        core_resources = self.jtag.core_mgr.resources
        m = Module()
        m.submodules.jtag = self.jtag
        m.submodules.sram = self.sram

        count = Signal(5)
        m.d.sync += count.eq(count+1)
        print ("resources", platform, jtag_resources.items())
        gpio = self.jtag_request('gpio')
        print (gpio, gpio.layout, gpio.fields)
        # get the GPIO bank, mess about with some of the pins
        m.d.comb += gpio.gpio0.o.eq(1)
        m.d.comb += gpio.gpio1.o.eq(gpio.gpio2.i)
        m.d.comb += gpio.gpio1.oe.eq(count[4])
        m.d.sync += count[0].eq(gpio.gpio1.i)
        # get the UART resource, mess with the output tx
        uart = self.jtag_request('uart')
        print (uart, uart.fields)
        intermediary = Signal()
        m.d.comb += uart.tx.eq(intermediary)
        m.d.comb += intermediary.eq(uart.rx)

        # platform requested: make the exact same requests,
        # then add JTAG afterwards
        if platform is not None:
            for (name, number, dir, xdr) in self.jtag.requests_made:
                asicpad = platform.request(name, number, dir=dir, xdr=xdr)
                jtagpad = self.jtag.resource_table_pads[(name, number)]
                print ("jtagpad", jtagpad, jtagpad.layout)
                m.d.comb += recurse_down(asicpad, jtagpad)

            # wire up JTAG otherwise we are in trouble (no clock)
            jtag = platform.request('jtag')
            m.d.comb += self.jtag.bus.tdi.eq(jtag.tdi)
            m.d.comb += self.jtag.bus.tck.eq(jtag.tck)
            m.d.comb += self.jtag.bus.tms.eq(jtag.tms)
            m.d.comb += jtag.tdo.eq(self.jtag.bus.tdo)

        # add the eq assignments connecting up JTAG boundary scan to core
        m.d.comb += self.jtag.eqs
        return m

    def ports(self):
        return list(self)

    def __iter__(self):
        yield self.jtag.bus.tdi
        yield self.jtag.bus.tdo
        yield self.jtag.bus.tck
        yield self.jtag.bus.tms
        yield from self.jtag.boundary_scan_pads

    def jtag_request(self, name, number=0, *, dir=None, xdr=None):
        return self.jtag.resource_table[(name, number)]

    def add_jtag_request(self, name, number=0, *, dir=None, xdr=None):
        """request a Resource (e.g. name="uart", number=0) which will
        return a data structure containing Records of all the pins.

        this override will also - automatically - create a JTAG Boundary Scan
        connection *without* any change to the actual Platform.request() API
        """
        pad_mgr = self.jtag.pad_mgr
        core_mgr = self.jtag.core_mgr
        padlookup = self.jtag.padlookup
        # okaaaay, bit of shenanigens going on: the important data structure
        # here is Resourcemanager._ports.  requests add to _ports, which is
        # what needs redirecting.  therefore what has to happen is to
        # capture the number of ports *before* the request. sigh.
        start_ports = len(core_mgr._ports)
        value = core_mgr.request(name, number, dir=dir, xdr=xdr)
        end_ports = len(core_mgr._ports)

        # take a copy of the requests made
        self.jtag.requests_made.append((name, number, dir, xdr))

        # now make a corresponding (duplicate) request to the pad manager
        # BUT, if it doesn't exist, don't sweat it: all it means is, the
        # application did not request Boundary Scan for that resource.
        pad_start_ports = len(pad_mgr._ports)
        pvalue = pad_mgr.request(name, number, dir=dir, xdr=xdr)
        pad_end_ports = len(pad_mgr._ports)

        # ok now we have the lengths: now create a lookup between the pad
        # and the core, so that JTAG boundary scan can be inserted in between
        core = core_mgr._ports[start_ports:end_ports]
        pads = pad_mgr._ports[pad_start_ports:pad_end_ports]
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
            padpin = pad[1]
            corepin = core[1]
            if padpin is None: continue # skip when pin is None
            assert corepin is not None # if pad was None, core should be too
            print ("iter", pad, padpin.name)
            print ("existing pads", padlookup.keys())
            assert padpin.name not in padlookup # no overwrites allowed!
            assert padpin.name == corepin.name       # has to be the same!
            padlookup[padpin.name] = pad        # store pad by pin name

            # now add the IO Shift Register.  first identify the type
            # then request a JTAG IOConn. we can't wire it up (yet) because
            # we don't have a Module() instance. doh. that comes in get_input
            # and get_output etc. etc.
            iotype = resiotypes[padpin.dir] # look up the C4M-JTAG IOType
            io = self.jtag.add_io(iotype=iotype, name=padpin.name) # IOConn
            self.jtag.ios[padpin.name] = io # store IOConn Record by pin name

            # and connect up core to pads based on type.  could create
            # Modules here just like in Platform.get_input/output but
            # in some ways it is clearer by being simpler to wire them globally

            if padpin.dir == 'i':
                print ("jtag_request add input pin", padpin)
                print ("                   corepin", corepin)
                print ("   jtag io core", io.core)
                print ("   jtag io pad", io.pad)
                # corepin is to be returned, here. so, connect jtag corein to it
                self.jtag.eqs += [corepin.i.eq(io.core.i)]
                # and padpin to JTAG pad
                self.jtag.eqs += [io.pad.i.eq(padpin.i)]
                self.jtag.boundary_scan_pads.append(padpin.i)
            elif padpin.dir == 'o':
                print ("jtag_request add output pin", padpin)
                print ("                    corepin", corepin)
                print ("   jtag io core", io.core)
                print ("   jtag io pad", io.pad)
                # corepin is to be returned, here. connect it to jtag core out
                self.jtag.eqs += [io.core.o.eq(corepin.o)]
                # and JTAG pad to padpin
                self.jtag.eqs += [padpin.o.eq(io.pad.o)]
                self.jtag.boundary_scan_pads.append(padpin.o)
            elif padpin.dir == 'io':
                print ("jtag_request add io    pin", padpin)
                print ("                   corepin", corepin)
                print ("   jtag io core", io.core)
                print ("   jtag io pad", io.pad)
                # corepin is to be returned, here. so, connect jtag corein to it
                self.jtag.eqs += [corepin.i.eq(io.core.i)]
                # and padpin to JTAG pad
                self.jtag.eqs += [io.pad.i.eq(padpin.i)]
                # corepin is to be returned, here. connect it to jtag core out
                self.jtag.eqs += [io.core.o.eq(corepin.o)]
                # and JTAG pad to padpin
                self.jtag.eqs += [padpin.o.eq(io.pad.o)]
                # corepin is to be returned, here. connect it to jtag core out
                self.jtag.eqs += [io.core.oe.eq(corepin.oe)]
                # and JTAG pad to padpin
                self.jtag.eqs += [padpin.oe.eq(io.pad.oe)]

                self.jtag.boundary_scan_pads.append(padpin.i)
                self.jtag.boundary_scan_pads.append(padpin.o)
                self.jtag.boundary_scan_pads.append(padpin.oe)

        # finally record the *CORE* value just like ResourceManager.request()
        # so that the module using this can connect to *CORE* i/o to the
        # resource.  pads are taken care of
        self.jtag.resource_table[(name, number)] = value

        # and the *PAD* value so that it can be wired up externally as well
        self.jtag.resource_table_pads[(name, number)] = pvalue


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
    command_templates = ['/bin/true'] # no command needed: stops barfing
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
        self.jtag = jtag
        super().__init__()

        # create set of pin resources based on the pinset, this is for the core
        #jtag_resources = self.jtag.pad_mgr.resources
        self.add_resources(resources)

        # add JTAG without scan
        self.add_resources([JTAGResource('jtag', 0)], no_boundary_scan=True)

    def add_resources(self, resources, no_boundary_scan=False):
        print ("ASICPlatform add_resources", resources)
        return super().add_resources(resources)

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
        m.d.comb += pin.i.eq(self._invert_if(invert, port))
        return m

    def get_output(self, pin, port, attrs, invert):
        self._check_feature("single-ended output", pin, attrs,
                            valid_xdrs=(0,), valid_attrs=None)

        m = Module()
        print ("    get_output", pin, "port", port, port.layout)
        m.d.comb += port.eq(self._invert_if(invert, pin.o))
        return m

    def get_tristate(self, pin, port, attrs, invert):
        self._check_feature("single-ended tristate", pin, attrs,
                            valid_xdrs=(0,), valid_attrs=None)

        print ("    get_tristate", pin, "port", port, port.layout)
        m = Module()
        print ("       pad", pin, port, attrs)
        print ("       pin", pin.layout)
        return m
        #    m.submodules += Instance("$tribuf",
        #        p_WIDTH=pin.width,
        #        i_EN=pin.oe,
        #        i_A=self._invert_if(invert, pin.o),
        #        o_Y=port,
        #    )
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
        print ("       port layout", port.layout)
        print ("       pin", pin)
        print ("            layout", pin.layout)
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

        m.d.comb += pin.i.eq(self._invert_if(invert, port_i))
        m.d.comb += port_o.eq(self._invert_if(invert, pin.o))
        m.d.comb += port_oe.eq(pin.oe)

        return m

    def toolchain_prepare(self, fragment, name, **kwargs):
        """override toolchain_prepare in order to grab the fragment
        """
        self.fragment = fragment
        return super().toolchain_prepare(fragment, name, **kwargs)

"""
and to create a Platform instance with that list, and build
something random

   p=Platform()
   p.resources=listofstuff
   p.build(Blinker())
"""
pinset = dummy_pinset()
print(pinset)
resources = create_resources(pinset)
top = Blinker(pinset, resources)

#vl = rtlil.convert(top, ports=top.ports())
#with open("test_jtag_blinker.il", "w") as f:
#    f.write(vl)

if True:
    # XXX these modules are all being added *AFTER* the build process links
    # everything together.  the expectation that this would work is...
    # unrealistic.  ordering, clearly, is important.

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

    p = ASICPlatform (resources, top.jtag)
    p.build(top)
    # this is what needs to gets treated as "top", after "main module" top
    # is augmented with IO pads with JTAG tacked on.  the expectation that
    # the get_input() etc functions will be called magically by some other
    # function is unrealistic.
    top_fragment = p.fragment

# XXX simulating top (the module that does not itself contain IO pads
# because that's covered by build) cannot possibly be expected to work
# particularly when modules have been added *after* the platform build()
# function has been called.

sim = Simulator(top)
sim.add_clock(1e-6, domain="sync")      # standard clock

sim.add_sync_process(wrap(jtag_srv(top))) #? jtag server
#if len(sys.argv) != 2 or sys.argv[1] != 'server':
sim.add_sync_process(wrap(jtag_sim(cdut, top.jtag))) # actual jtag tester
sim.add_sync_process(wrap(dmi_sim(top.jtag)))  # handles (pretends to be) DMI

with sim.write_vcd("dmi2jtag_test_srv.vcd"):
    sim.run()
