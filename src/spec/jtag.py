"""JTAG interface

using Staf Verhaegen (Chips4Makers) wishbone TAP

Pinmux documented here https://libre-soc.org/docs/pinmux/
"""

from nmigen.build.res import ResourceManager
from nmigen.hdl.rec import Layout
from collections import OrderedDict, defaultdict
from nmigen.cli import rtlil

from nmigen import (Module, Signal, Elaboratable, Cat)
from c4m.nmigen.jtag.tap import IOType, TAP

# map from pinmux to c4m jtag iotypes
iotypes = {'-': IOType.In,
           '+': IOType.Out,
           '>': IOType.TriOut,
           '*': IOType.InTriOut,
          }

# Resources
# nmigen Resources has a different encoding for direction: "i", "o", "io", "oe"
resiotypes = {'i': IOType.In,
              'o': IOType.Out,
              'oe': IOType.TriOut,
              'io': IOType.InTriOut,
             }

# How many bits in each signal type
scanlens = {IOType.In: 1,
            IOType.Out: 1,
            IOType.TriOut: 2,
            IOType.InTriOut: 3,
           }


def dummy_pinset():
    # sigh this needs to come from pinmux.
    gpios = []
    for i in range(16):
        gpios.append("%d*" % i)
    return {'uart': ['tx+', 'rx-'],
             'gpio': gpios,
             'i2c': ['sda*', 'scl+']}


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
                name, pin_type = pin[:-1], pin[-1]
                iotype = iotypes[pin_type]
                pin_name = "%s_%s" % (fn, name)
                yield (fn, name, iotype, pin_name, scan_idx)
                scan_idx += scanlens[iotype] # inc boundary reg scan offset


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


class JTAG(TAP, Pins):
    # 32-bit data width here.  use None to not add a wishbone interface
    def __init__(self, pinset, domain, wb_data_wid=32, resources=None):
        if resources is None:
            resources = []
        self.domain = domain
        TAP.__init__(self, ir_width=4)
        Pins.__init__(self, pinset)

        # enumerate pin specs and create IOConn Records.
        # we store the boundary scan register offset in the IOConn record
        self.ios = {} # these are enumerated in external_ports
        self.scan_len = 0
        self.add_pins(list(self))

        # this is redundant.  or maybe part of testing, i don't know.
        self.sr = self.add_shiftreg(ircode=4, length=3,
                                    domain=domain)

        # create and connect wishbone
        if wb_data_wid is not None:
            self.wb = self.add_wishbone(ircodes=[5, 6, 7], features={'err'},
                                   address_width=30, data_width=wb_data_wid,
                                   granularity=8, # 8-bit wide
                                   name="jtag_wb",
                                   domain=domain)

        # create DMI2JTAG (goes through to dmi_sim())
        self.dmi = self.add_dmi(ircodes=[8, 9, 10],
                                    domain=domain)

        # use this for enable/disable of parts of the ASIC.
        # XXX make sure to add the _en sig to en_sigs list
        self.wb_icache_en = Signal(reset=1)
        self.wb_dcache_en = Signal(reset=1)
        self.wb_sram_en = Signal(reset=1)
        self.en_sigs = en_sigs = Cat(self.wb_icache_en, self.wb_dcache_en,
                                     self.wb_sram_en)
        self.sr_en = self.add_shiftreg(ircode=11, length=len(en_sigs),
                                       domain=domain)

        # Platform Resource Mirror: enumerated by boundary_elaborate()
        # in order to make a transparent/auto wire-up of what would
        # normally be directly connected to IO Pads, to go instead
        # first through a JTAG Boundary Scan... *and then* get auto-
        # connected on ultimately to the IO Pads.  to do that, the best
        # API is one that reflects that of Platforms... and that means
        # using duplicate ResourceManagers so that the user may use
        # the exact same resource-requesting function, "request", and
        # may also use the exact same Resource list

        self.pad_mgr = ResourceManager([], [])
        self.core_mgr = ResourceManager([], [])
        self.pad_mgr.add_resources(resources)
        self.core_mgr.add_resources(resources)

        # record resource lookup between core IO names and pads
        self.padlookup = {}
        self.requests_made = []
        self.boundary_scan_pads = defaultdict(dict)
        self.resource_table = {}
        self.resource_table_pads = {}
        self.eqs = []                 # list of BS to core/pad connections

        # allocate all resources in advance in pad/core ResourceManagers
        # this is because whilst a completely new (different) platform is
        # passed in to elaborate()s every time, that cannot happen with
        # JTAG Boundary scanning: the resources are allocated *prior*
        # to elaborate() being called [from Simulation(), Platform.build(),
        # and many other sources, multiple times]

        for resource in resources:
            print ("JTAG resource", resource)
            if resource.name in ['clk', 'rst']: # hack
                continue
            self.add_jtag_resource(resource.name, resource.number)

    def add_pins(self, pinlist):
        for fn, pin, iotype, pin_name, scan_idx in pinlist:
            io = self.add_io(iotype=iotype, name=pin_name)
            io._scan_idx = scan_idx # hmm shouldn't really do this
            self.scan_len += scan_idx # record full length of boundary scan
            self.ios[pin_name] = io

    def elaborate(self, platform):
        m = super().elaborate(platform)
        m.d.comb += self.sr.i.eq(self.sr.o) # loopback as part of test?

        # provide way to enable/disable wishbone caches and SRAM
        # just in case of issues
        # see https://bugs.libre-soc.org/show_bug.cgi?id=520
        with m.If(self.sr_en.oe):
            m.d.sync += self.en_sigs.eq(self.sr_en.o)
        # also make it possible to read the enable/disable current state
        with m.If(self.sr_en.ie):
            m.d.comb += self.sr_en.i.eq(self.en_sigs)

        # create a fake "stall"
        #wb = self.wb
        #m.d.comb += wb.stall.eq(wb.cyc & ~wb.ack) # No burst support

        return m

    def boundary_elaborate(self, m, platform):
        jtag_resources = self.pad_mgr.resources
        core_resources = self.core_mgr.resources
        self.asic_resources = {}

        # platform requested: make the exact same requests,
        # then add JTAG afterwards
        if platform is not None:
            for (name, number, dir, xdr) in self.requests_made:
                asicpad = platform.request(name, number, dir=dir, xdr=xdr)
                self.asic_resources[(name, number)] = asicpad
                jtagpad = self.resource_table_pads[(name, number)]
                print ("jtagpad", jtagpad, jtagpad.layout)
                m.d.comb += recurse_down(asicpad, jtagpad)

            # wire up JTAG otherwise we are in trouble
            jtag = platform.request('jtag')
            m.d.comb += self.bus.tdi.eq(jtag.tdi)
            m.d.comb += self.bus.tck.eq(jtag.tck)
            m.d.comb += self.bus.tms.eq(jtag.tms)
            m.d.comb += jtag.tdo.eq(self.bus.tdo)

        # add the eq assignments connecting up JTAG boundary scan to core
        m.d.comb += self.eqs
        return m

    def external_ports(self):
        """create a list of ports that goes into the top level il (or verilog)
        """
        ports = super().external_ports()           # gets JTAG signal names
        ports += list(self.wb.fields.values())     # wishbone signals
        for io in self.ios.values():
            ports += list(io.core.fields.values()) # io "core" signals
            ports += list(io.pad.fields.values())  # io "pad" signals"
        return ports

    def ports(self):
        return list(self.iter_ports())

    def iter_ports(self):
        yield self.bus.tdi
        yield self.bus.tdo
        yield self.bus.tck
        yield self.bus.tms
        for pad in self.boundary_scan_pads.values():
            yield from pad.values()

    def request(self, name, number=0, *, dir=None, xdr=None):
        """looks like ResourceManager.request but can be called multiple times.
        """
        return self.resource_table[(name, number)]

    def add_jtag_resource(self, name, number=0, *, dir=None, xdr=None):
        """request a Resource (e.g. name="uart", number=0) which will
        return a data structure containing Records of all the pins.

        this override will also - automatically - create a JTAG Boundary Scan
        connection *without* any change to the actual Platform.request() API
        """
        pad_mgr = self.pad_mgr
        core_mgr = self.core_mgr
        padlookup = self.padlookup
        # okaaaay, bit of shenanigens going on: the important data structure
        # here is Resourcemanager._ports.  requests add to _ports, which is
        # what needs redirecting.  therefore what has to happen is to
        # capture the number of ports *before* the request. sigh.
        start_ports = len(core_mgr._ports)
        value = core_mgr.request(name, number, dir=dir, xdr=xdr)
        end_ports = len(core_mgr._ports)

        # take a copy of the requests made
        self.requests_made.append((name, number, dir, xdr))

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
            # note that self.padlookup and self.ios use the *exact* same
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
            io = self.add_io(iotype=iotype, name=padpin.name) # IOConn
            self.ios[padpin.name] = io # store IOConn Record by pin name

            # and connect up core to pads based on type.  could create
            # Modules here just like in Platform.get_input/output but
            # in some ways it is clearer by being simpler to wire them globally

            if padpin.dir == 'i':
                print ("jtag_request add input pin", padpin)
                print ("                   corepin", corepin)
                print ("   jtag io core", io.core)
                print ("   jtag io pad", io.pad)
                # corepin is to be returned, here. so, connect jtag corein to it
                self.eqs += [corepin.i.eq(io.core.i)]
                # and padpin to JTAG pad
                self.eqs += [io.pad.i.eq(padpin.i)]
                self.boundary_scan_pads[padpin.name]['i'] = padpin.i
            elif padpin.dir == 'o':
                print ("jtag_request add output pin", padpin)
                print ("                    corepin", corepin)
                print ("   jtag io core", io.core)
                print ("   jtag io pad", io.pad)
                # corepin is to be returned, here. connect it to jtag core out
                self.eqs += [io.core.o.eq(corepin.o)]
                # and JTAG pad to padpin
                self.eqs += [padpin.o.eq(io.pad.o)]
                self.boundary_scan_pads[padpin.name]['o'] = padpin.o
            elif padpin.dir == 'io':
                print ("jtag_request add io    pin", padpin)
                print ("                   corepin", corepin)
                print ("   jtag io core", io.core)
                print ("   jtag io pad", io.pad)
                # corepin is to be returned, here. so, connect jtag corein to it
                self.eqs += [corepin.i.eq(io.core.i)]
                # and padpin to JTAG pad
                self.eqs += [io.pad.i.eq(padpin.i)]
                # corepin is to be returned, here. connect it to jtag core out
                self.eqs += [io.core.o.eq(corepin.o)]
                # and JTAG pad to padpin
                self.eqs += [padpin.o.eq(io.pad.o)]
                # corepin is to be returned, here. connect it to jtag core out
                self.eqs += [io.core.oe.eq(corepin.oe)]
                # and JTAG pad to padpin
                self.eqs += [padpin.oe.eq(io.pad.oe)]

                self.boundary_scan_pads[padpin.name]['i'] = padpin.i
                self.boundary_scan_pads[padpin.name]['o'] = padpin.o
                self.boundary_scan_pads[padpin.name]['oe'] = padpin.oe

        # finally record the *CORE* value just like ResourceManager.request()
        # so that the module using this can connect to *CORE* i/o to the
        # resource.  pads are taken care of
        self.resource_table[(name, number)] = value

        # and the *PAD* value so that it can be wired up externally as well
        self.resource_table_pads[(name, number)] = pvalue

if __name__ == '__main__':
    pinset = dummy_pinset()
    dut = JTAG(pinset, "sync")

    vl = rtlil.convert(dut)
    with open("test_jtag.il", "w") as f:
        f.write(vl)

