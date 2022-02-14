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
from jtag import JTAG, resiotypes
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

from c4m.nmigen.jtag.tap import TAP, IOType
from c4m.nmigen.jtag.bus import Interface as JTAGInterface
from soc.debug.dmi import DMIInterface, DBGCore
#from soc.debug.test.dmi_sim import dmi_sim
#from soc.debug.test.jtagremote import JTAGServer, JTAGClient
from nmigen.build.res import ResourceError

# Was thinking of using these functions, but skipped for simplicity for now
# XXX nope.  the output from JSON file.
# from pinfunctions import (i2s, lpc, emmc, sdmmc, mspi, mquadspi, spi,
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
            # 'jtag': ['tms-', 'tdi-', 'tdo+', 'tck+'],
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
            print("GPIO is defined as '*' type, meaning i, o and oe needed")
            ios = []
            for pin in pins:
                pname = "gpio"+pin[:-1]  # strip "*" on end
                # urrrr... tristsate and io assume a single pin which is
                # of course exactly what we don't want in an ASIC: we want
                # *all three* pins but the damn port is not outputted
                # as a triplet, it's a single Record named "io". sigh.
                # therefore the only way to get a triplet of i/o/oe
                # is to *actually* create explicit triple pins
                # XXX ARRRGH, doesn't work
                # pad = Subsignal("io",
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


# top-level demo module.
class Blinker(Elaboratable):
    def __init__(self, pinset, resources, no_jtag_connect=False):
        self.no_jtag_connect = no_jtag_connect
        self.jtag = JTAG({}, "sync", resources=resources)
        #memory = Memory(width=32, depth=16)
        #self.sram = SRAM(memory=memory, bus=self.jtag.wb)

    def elaborate(self, platform):
        jtag_resources = self.jtag.pad_mgr.resources
        m = Module()
        m.submodules.jtag = self.jtag
        #m.submodules.sram = self.sram

        #count = Signal(5)
        #m.d.sync += count.eq(count+1)
        print("resources", platform, jtag_resources.items())
        gpio = self.jtag.request('gpio')
        print(gpio, gpio.layout, gpio.fields)
        # get the GPIO bank, mess about with some of the pins
        #m.d.comb += gpio.gpio0.o.eq(1)
        #m.d.comb += gpio.gpio1.o.eq(gpio.gpio2.i)
        #m.d.comb += gpio.gpio1.oe.eq(count[4])
        #m.d.sync += count[0].eq(gpio.gpio1.i)

        num_gpios = 4
        gpio_i_ro = Signal(num_gpios)
        gpio_o_test = Signal(num_gpios)
        gpio_oe_test = Signal(num_gpios)

        # Create a read-only copy of core-side GPIO input signals
        # for Simulation asserts
        m.d.comb += gpio_i_ro[0].eq(gpio.gpio0.i)
        m.d.comb += gpio_i_ro[1].eq(gpio.gpio1.i)
        m.d.comb += gpio_i_ro[2].eq(gpio.gpio2.i)
        m.d.comb += gpio_i_ro[3].eq(gpio.gpio3.i)

        # Wire up the output signal of each gpio by XOR'ing each bit of
        # gpio_o_test with gpio's input
        # Wire up each bit of gpio_oe_test signal to oe signal of each gpio.
        # Turn into a loop at some point, probably a way without
        # using get_attr()
        m.d.comb += gpio.gpio0.o.eq(gpio_o_test[0] ^ gpio.gpio0.i)
        m.d.comb += gpio.gpio1.o.eq(gpio_o_test[1] ^ gpio.gpio1.i)
        m.d.comb += gpio.gpio2.o.eq(gpio_o_test[2] ^ gpio.gpio2.i)
        m.d.comb += gpio.gpio3.o.eq(gpio_o_test[3] ^ gpio.gpio3.i)

        m.d.comb += gpio.gpio0.oe.eq(gpio_oe_test[0])# ^ gpio.gpio0.i)
        m.d.comb += gpio.gpio1.oe.eq(gpio_oe_test[1])# ^ gpio.gpio1.i)
        m.d.comb += gpio.gpio2.oe.eq(gpio_oe_test[2])# ^ gpio.gpio2.i)
        m.d.comb += gpio.gpio3.oe.eq(gpio_oe_test[3])# ^ gpio.gpio3.i)

        # get the UART resource, mess with the output tx
        uart = self.jtag.request('uart')
        print("uart fields", uart, uart.fields)
        self.uart_tx_test = Signal()
        #self.intermediary = Signal()
        #m.d.comb += uart.tx.eq(self.intermediary)
        #m.d.comb += self.intermediary.eq(uart.rx)
        # Allow tx to be controlled externally
        m.d.comb += uart.tx.eq(self.uart_tx_test ^ uart.rx)

        # I2C
        num_i2c = 1
        i2c_sda_oe_test = Signal(num_i2c)
        i2c_scl_oe_test = Signal(num_i2c)
        i2c = self.jtag.request('i2c')
        print("i2c fields", i2c, i2c.fields)
        # Connect in loopback
        m.d.comb += i2c.sda.o.eq(i2c.sda.i)
        m.d.comb += i2c.scl.o.eq(i2c.scl.i)
        # Connect output enable to test port for sim
        m.d.comb += i2c.sda.oe.eq(i2c_sda_oe_test)# ^ i2c.sda.i)
        m.d.comb += i2c.scl.oe.eq(i2c_scl_oe_test)# ^ i2c.scl.i)

        # to even be able to get at objects, you first have to make them
        # available - i.e. not as local variables
        # Public attributes are equivalent to input/output ports in hdl's
        self.gpio = gpio
        self.uart = uart
        self.uart_tx_test
        self.i2c = i2c
        self.i2c_sda_oe_test = i2c_sda_oe_test
        self.i2c_scl_oe_test = i2c_scl_oe_test
        self.gpio_i_ro = gpio_i_ro
        self.gpio_o_test = gpio_o_test
        self.gpio_oe_test = gpio_oe_test

        # sigh these wire up to the pads so you cannot set Signals
        # that are already wired
        if self.no_jtag_connect:  # bypass jtag pad connect for testing purposes
            return m
        return self.jtag.boundary_elaborate(m, platform)

    def ports(self):
        return list(self)

    def __iter__(self):
        yield from self.jtag.iter_ports()


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
    command_templates = ['/bin/true']  # no command needed: stops barfing
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
    default_clk = "clk"  # should be picked up / overridden by platform sys.clk
    default_rst = "rst"  # should be picked up / overridden by platform sys.rst

    def __init__(self, resources, jtag):
        self.jtag = jtag
        super().__init__()

        # create set of pin resources based on the pinset, this is for the core
        #jtag_resources = self.jtag.pad_mgr.resources
        self.add_resources(resources)

        # add JTAG without scan
        self.add_resources([JTAGResource('jtag', 0)], no_boundary_scan=True)

    def add_resources(self, resources, no_boundary_scan=False):
        print("ASICPlatform add_resources", resources)
        return super().add_resources(resources)

    # def iter_ports(self):
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
        print("    get_input", pin, "port", port, port.layout)
        m.d.comb += pin.i.eq(self._invert_if(invert, port))
        return m

    def get_output(self, pin, port, attrs, invert):
        self._check_feature("single-ended output", pin, attrs,
                            valid_xdrs=(0,), valid_attrs=None)

        m = Module()
        print("    get_output", pin, "port", port, port.layout)
        m.d.comb += port.eq(self._invert_if(invert, pin.o))
        return m

    def get_tristate(self, pin, port, attrs, invert):
        self._check_feature("single-ended tristate", pin, attrs,
                            valid_xdrs=(0,), valid_attrs=None)

        print("    get_tristate", pin, "port", port, port.layout)
        m = Module()
        print("       pad", pin, port, attrs)
        print("       pin", pin.layout)
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

        print("    get_input_output", pin, "port", port, port.layout)
        m = Module()
        print("       port layout", port.layout)
        print("       pin", pin)
        print("            layout", pin.layout)
        # m.submodules += Instance("$tribuf",
        #    p_WIDTH=pin.width,
        #    i_EN=io.pad.oe,
        #    i_A=self._invert_if(invert, io.pad.o),
        #    o_Y=port,
        # )
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


def test_case0():
    print("Starting sanity test case!")
    print("printing out list of stuff in top")
    print("JTAG IOs", top.jtag.ios)
    # ok top now has a variable named "gpio", let's enumerate that too
    print("printing out list of stuff in top.gpio and its type")
    print(top.gpio.__class__.__name__, dir(top.gpio))
    # ok, it's a nmigen Record, therefore it has a layout.  let's print
    # that too
    print("top.gpio is a Record therefore has fields and a layout")
    print("    layout:", top.gpio.layout)
    print("    fields:", top.gpio.fields)
    print("Fun never ends...")
    print("    layout, gpio2:", top.gpio.layout['gpio2'])
    print("    fields, gpio2:", top.gpio.fields['gpio2'])
    print(top.jtag.__class__.__name__, dir(top.jtag))
    print("Pads:")
    print(top.jtag.resource_table_pads[('gpio', 0)])

    # etc etc. you get the general idea
    delayVal = 0.2e-6
    yield top.uart.rx.eq(0)
    yield Delay(delayVal)
    yield Settle()
    yield top.gpio.gpio2.o.eq(0)
    yield top.gpio.gpio3.o.eq(1)
    yield
    yield top.gpio.gpio3.oe.eq(1)
    yield
    yield top.gpio.gpio3.oe.eq(0)
    # grab the JTAG resource pad
    gpios_pad = top.jtag.resource_table_pads[('gpio', 0)]
    yield gpios_pad.gpio3.i.eq(1)
    yield Delay(delayVal)
    yield Settle()
    yield top.gpio.gpio2.oe.eq(1)
    yield top.gpio.gpio3.oe.eq(1)
    yield gpios_pad.gpio3.i.eq(0)
    yield top.jtag.gpio.gpio2.i.eq(1)
    yield Delay(delayVal)
    yield Settle()
    gpio_o2 = 0
    for _ in range(20):
        # get a value first (as an integer).  you were trying to set
        # it to the actual Signal.  this is not going to work.  or if
        # it does, it's very scary.
        gpio_o2 = not gpio_o2
        yield top.gpio.gpio2.o.eq(gpio_o2)

        # ditto: here you are trying to set to an AST expression
        # which is inadviseable (likely to fail)
        gpio_o3 = not gpio_o2
        yield top.gpio.gpio3.o.eq(gpio_o3)
        yield Delay(delayVal)
        yield Settle()
        # grab the JTAG resource pad
        uart_pad = top.jtag.resource_table_pads[('uart', 0)]
        yield uart_pad.rx.i.eq(gpio_o2)
        yield Delay(delayVal)
        yield Settle()
        yield  # one clock cycle
        tx_val = yield uart_pad.tx.o
        print("xmit uart", tx_val, gpio_o2)

    print("jtag pad table keys")
    print(top.jtag.resource_table_pads.keys())
    uart_pad = top.jtag.resource_table_pads[('uart', 0)]
    print("uart pad", uart_pad)
    print("uart pad", uart_pad.layout)

    yield top.gpio.gpio2.oe.eq(0)
    yield top.gpio.gpio3.oe.eq(0)
    yield top.jtag.gpio.gpio2.i.eq(0)
    yield Delay(delayVal)
    yield Settle()


def test_gpios(dut):
    print("Starting GPIO test case!")
    # TODO: make pad access parametrisable to cope with more than 4 GPIOs
    num_gpios = dut.gpio_o_test.width
    # Grab GPIO outpud pad resource from JTAG BS - end of chain
    print(dut.jtag.boundary_scan_pads.keys())
    gpio0_o = dut.jtag.boundary_scan_pads['gpio_0__gpio0__o']['o']
    gpio1_o = dut.jtag.boundary_scan_pads['gpio_0__gpio1__o']['o']
    gpio2_o = dut.jtag.boundary_scan_pads['gpio_0__gpio2__o']['o']
    gpio3_o = dut.jtag.boundary_scan_pads['gpio_0__gpio3__o']['o']
    gpio_pad_out = [gpio0_o, gpio1_o, gpio2_o, gpio3_o]

    # Grab GPIO output enable pad resource from JTAG BS - end of chain
    gpio0_oe = dut.jtag.boundary_scan_pads['gpio_0__gpio0__oe']['o']
    gpio1_oe = dut.jtag.boundary_scan_pads['gpio_0__gpio1__oe']['o']
    gpio2_oe = dut.jtag.boundary_scan_pads['gpio_0__gpio2__oe']['o']
    gpio3_oe = dut.jtag.boundary_scan_pads['gpio_0__gpio3__oe']['o']
    gpio_pad_oe = [gpio0_oe, gpio1_oe, gpio2_oe, gpio3_oe]

    # Grab GPIO input pad resource from JTAG BS - start of chain
    gpio0_pad_in = dut.jtag.boundary_scan_pads['gpio_0__gpio0__i']['i']
    gpio1_pad_in = dut.jtag.boundary_scan_pads['gpio_0__gpio1__i']['i']
    gpio2_pad_in = dut.jtag.boundary_scan_pads['gpio_0__gpio2__i']['i']
    gpio3_pad_in = dut.jtag.boundary_scan_pads['gpio_0__gpio3__i']['i']
    gpio_pad_in = [gpio0_pad_in, gpio1_pad_in, gpio2_pad_in, gpio3_pad_in]

    # Have the sim run through a for-loop where the gpio_o_test is
    # incremented like a counter (0000, 0001...)
    # At each iteration of the for-loop, assert:
    # + output set at core matches output seen at pad
    # TODO + input set at pad matches input seen at core
    # TODO + if gpio_o_test bit is cleared, output seen at pad matches
    # input seen at pad
    num_gpio_o_states = num_gpios**2
    pad_out = [0] * num_gpios
    pad_oe = [0] * num_gpios
    #print("Num of permutations of gpio_o_test record: ", num_gpio_o_states)
    for gpio_o_val in range(0, num_gpio_o_states):
        yield dut.gpio_o_test.eq(gpio_o_val)
        # yield Settle()
        yield  # Move to the next clk cycle

        # Cycle through all input combinations
        for gpio_i_val in range(0, num_gpio_o_states):
            # Set each gpio input at pad to test value
            for gpio_bit in range(0, num_gpios):
                yield gpio_pad_in[gpio_bit].eq((gpio_i_val >> gpio_bit) & 0x1)
            yield
            # After changing the gpio0/1/2/3 inputs,
            # the output is also going to change.
            # *therefore it must be read again* to get the
            # snapshot (as a python value)
            for gpio_bit in range(0, num_gpios):
                pad_out[gpio_bit] = yield gpio_pad_out[gpio_bit]
            yield
            for gpio_bit in range(0, num_gpios):
                # check core and pad in
                gpio_i_ro = yield dut.gpio_i_ro[gpio_bit]
                out_test_bit = ((gpio_o_val & (1 << gpio_bit)) != 0)
                in_bit = ((gpio_i_val & (1 << gpio_bit)) != 0)
                # Check that the core end input matches pad
                assert in_bit == gpio_i_ro
                # Test that the output at pad matches:
                # Pad output == given test output XOR test input
                assert (out_test_bit ^ in_bit) == pad_out[gpio_bit]

            # For debugging - VERY verbose
            # print("---------------------")
            #print("Test Out: ", bin(gpio_o_val))
            #print("Test Input: ", bin(gpio_i_val))
            # Print MSB first
            #print("Pad Output: ", list(reversed(pad_out)))
            # print("---------------------")

    # For-loop for testing output enable signals
    for gpio_o_val in range(0, num_gpio_o_states):
        yield dut.gpio_oe_test.eq(gpio_o_val)
        yield  # Move to the next clk cycle

        for gpio_bit in range(0, num_gpios):
            pad_oe[gpio_bit] = yield gpio_pad_oe[gpio_bit]
        yield

        for gpio_bit in range(0, num_gpios):
            oe_test_bit = ((gpio_o_val & (1 << gpio_bit)) != 0)
            # oe set at core matches oe seen at pad:
            assert oe_test_bit == pad_oe[gpio_bit]
        # For debugging - VERY verbose
        # print("---------------------")
        #print("Test Output Enable: ", bin(gpio_o_val))
        # Print MSB first
        #print("Pad Output Enable: ", list(reversed(pad_oe)))
        # print("---------------------")

    # Reset test ouput register
    yield dut.gpio_o_test.eq(0)
    print("GPIO Test PASSED!")


def test_uart(dut):
    # grab the JTAG resource pad
    print()
    print("bs pad keys", dut.jtag.boundary_scan_pads.keys())
    print()
    uart_rx_pad = dut.jtag.boundary_scan_pads['uart_0__rx']['i']
    uart_tx_pad = dut.jtag.boundary_scan_pads['uart_0__tx']['o']

    print("uart rx pad", uart_rx_pad)
    print("uart tx pad", uart_tx_pad)

    # Test UART by writing 0 and 1 to RX
    # Internally TX connected to RX,
    # so match pad TX with RX
    for i in range(0, 2):
        yield uart_rx_pad.eq(i)
        # yield uart_rx_pad.eq(i)
        yield Settle()
        yield  # one clock cycle
        tx_val = yield uart_tx_pad
        print("xmit uart", tx_val, 1)
        assert tx_val == i

    print("UART Test PASSED!")


def test_i2c(dut):
    i2c_sda_i_pad = dut.jtag.boundary_scan_pads['i2c_0__sda__i']['i']
    i2c_sda_o_pad = dut.jtag.boundary_scan_pads['i2c_0__sda__o']['o']
    i2c_sda_oe_pad = dut.jtag.boundary_scan_pads['i2c_0__sda__oe']['o']

    i2c_scl_i_pad = dut.jtag.boundary_scan_pads['i2c_0__scl__i']['i']
    i2c_scl_o_pad = dut.jtag.boundary_scan_pads['i2c_0__scl__o']['o']
    i2c_scl_oe_pad = dut.jtag.boundary_scan_pads['i2c_0__scl__oe']['o']

    #i2c_pad = dut.jtag.resource_table_pads[('i2c', 0)]
    #print ("i2c pad", i2c_pad)
    #print ("i2c pad", i2c_pad.layout)

    for i in range(0, 2):
        yield i2c_sda_i_pad.eq(i)  # i2c_pad.sda.i.eq(i)
        yield i2c_scl_i_pad.eq(i)  # i2c_pad.scl.i.eq(i)
        yield dut.i2c_sda_oe_test.eq(i)
        yield dut.i2c_scl_oe_test.eq(i)
        yield Settle()
        yield  # one clock cycle
        sda_o_val = yield i2c_sda_o_pad
        scl_o_val = yield i2c_scl_o_pad
        sda_oe_val = yield i2c_sda_oe_pad
        scl_oe_val = yield i2c_scl_oe_pad
        print("Test input: ", i, " SDA/SCL out: ", sda_o_val, scl_o_val,
              " SDA/SCL oe: ", sda_oe_val, scl_oe_val)
        assert sda_o_val == i
        assert scl_o_val == i
        assert sda_oe_val == i
        assert scl_oe_val == i

    print("I2C Test PASSED!")

# JTAG boundary scan reg addresses - See c4m/nmigen/jtag/tap.py line #357
BS_EXTEST = 0
BS_INTEST = 0
BS_SAMPLE = 2
BS_PRELOAD = 2

def test_jtag_bs_chain(dut):
    # print(dir(dut.jtag))
    # print(dir(dut))
    # print(dut.jtag._ir_width)
    # print("JTAG I/O dictionary of core/pad signals:")
    # print(dut.jtag.ios.keys())

    print("JTAG BS Reset")
    yield from jtag_set_reset(dut.jtag)

    # TODO: cleanup!
    # Based on number of ios entries, produce a test shift reg pattern
    bslen = len(dut.jtag.ios)
    #fulldata = bsdata  # for testing
    #emptydata = 0  # for testing

    mask_i = produce_ios_mask(dut, is_i=True, is_o=False, is_oe=False)
    mask_i_oe = produce_ios_mask(dut, is_i=True, is_o=False, is_oe=True)
    mask_o = produce_ios_mask(dut, is_i=False, is_o=True, is_oe=False)
    mask_oe = produce_ios_mask(dut, is_i=False, is_o=False, is_oe=True)
    mask_o_oe = produce_ios_mask(dut, is_i=False, is_o=True, is_oe=True)
    mask_low = 0
    mask_all = 2**bslen - 1

    num_bit_format = "{:0" + str(bslen) + "b}"
    print("Masks (LSB corresponds to bit0 of the BS chain register!)")
    print("Input  only  :", num_bit_format.format(mask_i))
    print("Input  and oe:", num_bit_format.format(mask_o_oe))
    print("Output only  :", num_bit_format.format(mask_o))
    print("Out en only  :", num_bit_format.format(mask_oe))
    print("Output and oe:", num_bit_format.format(mask_o_oe))

    bsdata = mask_all

    yield from jtag_unit_test(dut, BS_EXTEST, False, bsdata, mask_o_oe, mask_o)
    yield from jtag_unit_test(dut, BS_SAMPLE, False, bsdata, mask_low, mask_low)

    # Run through GPIO, UART, and I2C tests so that all signals are asserted
    yield from test_gpios(dut)
    yield from test_uart(dut)
    yield from test_i2c(dut)

    bsdata = mask_low
    yield from jtag_unit_test(dut, BS_EXTEST, True, bsdata, mask_i, mask_i_oe)
    yield from jtag_unit_test(dut, BS_SAMPLE, True, bsdata, mask_all, mask_all)

    print("JTAG Boundary Scan Chain Test PASSED!")

# ONLY NEEDED FOR DEBUG - MAKE SURE TAP DRIVER FUNCTIONS CORRECT FIRST!
def swap_bit_order(word, wordlen):
    rev_word = 0
    for i in range(wordlen):
        rev_word += ((word >> i) & 0x1) << (wordlen-1-i)

    num_bit_format = "{:0" + str(wordlen) + "b}"
    print_str = "Orig:" + num_bit_format + " | Bit Swapped:" + num_bit_format
    print(print_str.format(word, rev_word))

    return rev_word

def jtag_unit_test(dut, bs_type, is_io_set, bsdata, exp_pads, exp_tdo):
    bslen = len(dut.jtag.ios) #* 2
    print("Chain len based on jtag.ios: {}".format(bslen))
    if bs_type == BS_EXTEST:
        print("Sending TDI data with core/pads disconnected")
    elif bs_type == BS_SAMPLE:
        print("Sending TDI data with core/pads connected")
    else:
        raise Exception("Unsupported BS chain mode!")

    if is_io_set:
        print("All pad inputs/core outputs set, bs data: {0:b}"
              .format(bsdata))
    else:
        print("All pad inputs/core outputs reset, bs data: {0:b}"
              .format(bsdata))

    result = yield from jtag_read_write_reg(dut.jtag, bs_type, bslen, bsdata,
                                            reverse=True)
    if bs_type == BS_EXTEST:
        # TDO is only outputting previous BS chain data, must configure to
        # output BS chain to the main shift register
        yield from jtag_set_shift_dr(dut.jtag)
        result = yield from tms_data_getset(dut.jtag, bs_type, bslen, bsdata,
                                            reverse=True)
        yield from jtag_set_idle(dut.jtag)

    # TODO: make format based on bslen, not a magic number 20-bits wide
    print("TDI BS Data: {0:020b}, Data Length (bits): {1}"
            .format(bsdata, bslen))
    print("TDO BS Data: {0:020b}".format(result))
    yield from check_ios_keys(dut, result, exp_pads, exp_tdo)

    #yield # testing extra clock
    # Reset shift register between tests
    yield from jtag_set_reset(dut.jtag)

def check_ios_keys(dut, tdo_data, test_vector, exp_tdo):
    print("Checking ios signals with TDO and given test vectors")
    bslen = len(dut.jtag.ios)
    ios_keys = list(dut.jtag.ios.keys())
    print(" ios Signals  |   From TDO    | --- | ----")
    print("Side|Exp|Seen | Side|Exp|Seen | I/O | Name")
    for i in range(0, bslen):
        signal = ios_keys[i]
        exp_pad_val = (test_vector >> i) & 0b1
        exp_tdo_val = (exp_tdo >> i) & 0b1
        tdo_value = (tdo_data >> i) & 0b1
        # Only observed signals so far are outputs...
        # TODO: Cleanup!
        if check_if_signal_output(ios_keys[i]):
            temp_result = yield dut.jtag.boundary_scan_pads[signal]['o']
            print("Pad |{0:3b}|{1:4b} | Core|{2:3b}|{3:4b} |  o  | {4}"
            .format(exp_pad_val, temp_result, exp_tdo_val, tdo_value, signal))
        # ...or inputs
        elif check_if_signal_input(ios_keys[i]):
            temp_result = yield dut.jtag.boundary_scan_pads[signal]['i']
            print("Pad |{0:3b}|{1:4b} | Pad |{2:3b}|{3:4b} |  i  | {4}"
            .format(exp_pad_val, temp_result, exp_tdo_val, tdo_value, signal))
        else:
            raise Exception("Signal in JTAG ios dict: " + signal
                            + " cannot be determined as input or output!")
        assert temp_result == exp_pad_val
        assert tdo_value == exp_tdo_val

# TODO: may need to expand to support further signals contained in the
# JTAG module ios dictionary!


def check_if_signal_output(signal_str):
    if ('__o' in signal_str) or ('__tx' in signal_str):
        return True
    else:
        return False


def check_if_signal_input(signal_str):
    if ('__i' in signal_str) or ('__rx' in signal_str):
        return True
    else:
        return False


def produce_ios_mask(dut, is_i=False, is_o=True, is_oe=False):
    if is_i and not(is_o) and not(is_oe):
        mask_type = "input"
    elif not(is_i) and is_o:
        mask_type = "output"
    else:
        mask_type = "i={:b} | o={:b} | oe={:b} ".format(is_i, is_o, is_oe)
    print("Determine the", mask_type, "mask")
    bslen = len(dut.jtag.ios)
    ios_keys = list(dut.jtag.ios.keys())
    mask = 0
    for i in range(0, bslen):
        signal = ios_keys[i]
        if (('__o' in ios_keys[i]) or ('__tx' in ios_keys[i])):
            if ('__oe' in ios_keys[i]):
                if is_oe:
                    mask += (1 << i)
            else:
                if is_o:
                    mask += (1 << i)
        else:
            if is_i:
                mask += (1 << i)
    return mask


def print_all_ios_keys(dut):
    print("Print all ios keys")
    bslen = len(dut.jtag.ios)
    ios_keys = list(dut.jtag.ios.keys())
    for i in range(0, bslen):
        signal = ios_keys[i]
        # Check if outputs are asserted
        if ('__o' in ios_keys[i]) or ('__tx' in ios_keys[i]):
            print("Pad Output | Name: ", signal)
        else:
            print("Pad  Input | Name: ", signal)


# Copied from test_jtag_tap.py
# JTAG-ircodes for accessing DMI
DMI_ADDR = 5
DMI_READ = 6
DMI_WRRD = 7

# JTAG-ircodes for accessing Wishbone
WB_ADDR = 8
WB_READ = 9
WB_WRRD = 10


def test_jtag_dmi_wb():
    print(dir(top.jtag))
    print(dir(top))
    print("JTAG BS Reset")
    yield from jtag_set_reset(top.jtag)

    print("JTAG I/O dictionary of core/pad signals:")
    print(top.jtag.ios.keys())

    # Copied from test_jtag_tap
    # Don't know if the ID is the same for all JTAG instances
    ####### JTAGy stuff (IDCODE) ######

    # read idcode
    idcode = yield from jtag_read_write_reg(top.jtag, 0b1, 32)
    print("idcode", hex(idcode))
    assert idcode == 0x18ff

    ####### JTAG to DMI ######

    # write DMI address
    yield from jtag_read_write_reg(top.jtag, DMI_ADDR, 8, DBGCore.CTRL)

    # read DMI CTRL register
    status = yield from jtag_read_write_reg(top.jtag, DMI_READ, 64)
    print("dmi ctrl status", hex(status))
    #assert status == 4

    # write DMI address
    yield from jtag_read_write_reg(top.jtag, DMI_ADDR, 8, 0)

    # write DMI CTRL register
    status = yield from jtag_read_write_reg(top.jtag, DMI_WRRD, 64, 0b101)
    print("dmi ctrl status", hex(status))
    # assert status == 4 # returned old value (nice! cool feature!)

    # write DMI address
    yield from jtag_read_write_reg(top.jtag, DMI_ADDR, 8, DBGCore.CTRL)

    # read DMI CTRL register
    status = yield from jtag_read_write_reg(top.jtag, DMI_READ, 64)
    print("dmi ctrl status", hex(status))
    #assert status == 6

    # write DMI MSR address
    yield from jtag_read_write_reg(top.jtag, DMI_ADDR, 8, DBGCore.MSR)

    # read DMI MSR register
    msr = yield from jtag_read_write_reg(top.jtag, DMI_READ, 64)
    print("dmi msr", hex(msr))
    #assert msr == 0xdeadbeef

    ####### JTAG to Wishbone ######

    # write Wishbone address
    yield from jtag_read_write_reg(top.jtag, WB_ADDR, 16, 0x18)

    # write/read wishbone data
    data = yield from jtag_read_write_reg(top.jtag, WB_WRRD, 16, 0xfeef)
    print("wb write", hex(data))

    # write Wishbone address
    yield from jtag_read_write_reg(top.jtag, WB_ADDR, 16, 0x18)

    # write/read wishbone data
    data = yield from jtag_read_write_reg(top.jtag, WB_READ, 16, 0)
    print("wb read", hex(data))

    ####### done - tell dmi_sim to stop (otherwise it won't) ########

    top.jtag.stop = True


def test_debug_print(dut):
    print("Test used for getting object methods/information")
    print("Moved here to clear clutter of gpio test")

    print("printing out info about the resource gpio0")
    print(dut.gpio['gpio0']['i'])
    print("this is a PIN resource", type(dut.gpio['gpio0']['i']))
    # yield can only be done on SIGNALS or RECORDS,
    # NOT Pins/Resources gpio0_core_in = yield top.gpio['gpio0']['i']
    #print("Test gpio0 core in: ", gpio0_core_in)

    print("JTAG")
    print(dut.jtag.__class__.__name__, dir(dut.jtag))
    print("TOP")
    print(dut.__class__.__name__, dir(dut))
    print("PORT")
    print(dut.ports.__class__.__name__, dir(dut.ports))
    print("GPIO")
    print(dut.gpio.__class__.__name__, dir(dut.gpio))

    print("UART")
    print(dir(dut.jtag.boundary_scan_pads['uart_0__rx__pad__i']))
    print(dut.jtag.boundary_scan_pads['uart_0__rx__pad__i'].keys())
    print(dut.jtag.boundary_scan_pads['uart_0__tx__pad__o'])
    # print(type(dut.jtag.boundary_scan_pads['uart_0__rx__pad__i']['rx']))
    print("jtag pad table keys")
    print(dut.jtag.resource_table_pads.keys())
    print(type(dut.jtag.resource_table_pads[('uart', 0)].rx.i))
    print(dut.jtag.boundary_scan_pads['uart_0__rx__i'])

    print("I2C")
    print(dut.jtag.boundary_scan_pads['i2c_0__sda__i'])
    print(type(dut.jtag.boundary_scan_pads['i2c_0__sda__i']['i']))

    print(dut.jtag.resource_table_pads)
    print(dut.jtag.boundary_scan_pads)

    # Trying to read input from core side, looks like might be a pin...
    # XXX don't "look like" - don't guess - *print it out*
    #print ("don't guess, CHECK", type(top.gpio.gpio0.i))

    print()  # extra print to divide the output
    yield


def setup_blinker(build_blinker=False):
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
    top = Blinker(pinset, resources, no_jtag_connect=False)  # True)

    vl = rtlil.convert(top, ports=top.ports())
    with open("test_jtag_blinker.il", "w") as f:
        f.write(vl)

    if build_blinker:
        # XXX these modules are all being added *AFTER* the build process links
        # everything together.  the expectation that this would work is...
        # unrealistic.  ordering, clearly, is important.

        # This JTAG code copied from test, probably not needed
        # dut = JTAG(test_pinset(), wb_data_wid=64, domain="sync")
        top.jtag.stop = False
        # rather than the client access the JTAG bus directly
        # create an alternative that the client sets

        class Dummy:
            pass
        cdut = Dummy()
        cdut.cbus = JTAGInterface()

        # set up client-server on port 44843-something
        top.jtag.s = JTAGServer()
        cdut.c = JTAGClient()
        top.jtag.s.get_connection()
        # else:
        #    print ("running server only as requested,
        #           use openocd remote to test")
        #    sys.stdout.flush()
        #    top.jtag.s.get_connection(None) # block waiting for connection

        # take copy of ir_width and scan_len
        cdut._ir_width = top.jtag._ir_width
        cdut.scan_len = top.jtag.scan_len

        p = ASICPlatform(resources, top.jtag)
        p.build(top)
        # this is what needs to gets treated as "top", after "main module" top
        # is augmented with IO pads with JTAG tacked on.  the expectation that
        # the get_input() etc functions will be called magically by some other
        # function is unrealistic.
        top_fragment = p.fragment

    return top


def test_jtag():
    dut = setup_blinker(build_blinker=False)

    # XXX simulating top (the module that does not itself contain IO pads
    # because that's covered by build) cannot possibly be expected to work
    # particularly when modules have been added *after* the platform build()
    # function has been called.

    sim = Simulator(dut)
    sim.add_clock(1e-6, domain="sync")      # standard clock

    # sim.add_sync_process(wrap(jtag_srv(top))) #? jtag server
    # if len(sys.argv) != 2 or sys.argv[1] != 'server':
    # actual jtag tester
    #sim.add_sync_process(wrap(jtag_sim(cdut, top.jtag)))
    # handles (pretends to be) DMI
    # sim.add_sync_process(wrap(dmi_sim(top.jtag)))

    # sim.add_sync_process(wrap(test_gpios(top)))
    # sim.add_sync_process(wrap(test_uart(top)))
    # sim.add_sync_process(wrap(test_i2c(top)))
    # sim.add_sync_process(wrap(test_debug_print()))

    sim.add_sync_process(wrap(test_jtag_bs_chain(dut)))

    with sim.write_vcd("blinker_test.vcd"):
        sim.run()

    # GTKWave doc generation
    style = {
        '': {'base': 'dec'},
        'in': {'color': 'orange'},
        'out': {'color': 'yellow'},
        'pad_i': {'color': 'orange'},
        'pad_o': {'color': 'yellow'},
        'core_i': {'color': 'indigo'},
        'core_o': {'color': 'blue'},
        'debug': {'module': 'top', 'color': 'red'}
    }
    traces = [
        ('ios', [
            ('uart_0__rx__pad__i', 'pad_i'),
            ('uart_0__tx__core__o', 'core_o'),
            ('gpio_0__gpio0__i__pad__i', 'pad_i'),
            ('gpio_0__gpio0__o__core__o', 'core_o'),
            ('gpio_0__gpio0__oe__core__o', 'core_o'),
            ('gpio_0__gpio1__i__pad__i', 'pad_i'),
            ('gpio_0__gpio1__o__core__o', 'core_o'),
            ('gpio_0__gpio1__oe__core__o', 'core_o'),
            ('gpio_0__gpio2__i__pad__i', 'pad_i'),
            ('gpio_0__gpio2__o__core__o', 'core_o'),
            ('gpio_0__gpio2__oe__core__o', 'core_o'),
            ('gpio_0__gpio3__i__pad__i', 'pad_i'),
            ('gpio_0__gpio3__o__core__o', 'core_o'),
            ('gpio_0__gpio3__oe__core__o', 'core_o'),
            ('i2c_0__sda__i__pad__i', 'pad_i'),
            ('i2c_0__sda__o__core__o', 'core_o'),
            ('i2c_0__sda__oe__core__o', 'core_o'),
            ('i2c_0__scl__i__pad__i', 'pad_i'),
            ('i2c_0__scl__o__core__o', 'core_o'),
            ('i2c_0__scl__oe__core__o', 'core_o')
        ]),
        ('JTAG', [
            'fsm.TAP_bus__tck',
            ('fsm.TAP_bus__tms', 'in'),
            ('TAP_bus__tdi', 'in'),
            ('TAP_bus__tdo', 'out'),
            'fsm.fsm_state'
        ]),
        ('JTAG internal', [
            ('io_bd2core', 'in'),
            ('io_bd2io', 'in'),
            ('io_bd[19:0]', {'base': 'hex'}),
            'io_sr[19:0]', {'base': 'hex'},
            ('io_capture', 'in'),
            ('io_shift', 'in'),
            'ir[3:0]', {'base': 'hex'},
            ('io_update', 'in'),
            ('io_isdr', 'in'),
            ('io_isir', 'in')
        ])
    ]

    write_gtkw("jtag_blinker.gtkw", "blinker_test.vcd", traces, style, module="top.jtag")

if __name__ == '__main__':
    test_jtag()
