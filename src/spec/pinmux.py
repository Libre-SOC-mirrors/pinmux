"""
1-bit pinmux case

"""
from random import randint
#from math import ceil, floor
from nmigen import Elaboratable, Module, Signal, Record, Array, Cat
from nmigen.hdl.rec import Layout
from nmigen.utils import log2_int
from nmigen.cli import rtlil
from soc.minerva.wishbone import make_wb_layout
from nmutil.util import wrap
#from soc.bus.test.wb_rw import wb_read, wb_write

from nmutil.gtkw import write_gtkw

cxxsim = False
if cxxsim:
    from nmigen.sim.cxxsim import Simulator, Settle, Delay
else:
    from nmigen.sim import Simulator, Settle, Delay

from iomux import IOMuxBlockSingle, io_layout
from simple_gpio import SimpleGPIO, GPIOManager, csrbus_layout

dummy_pinspec = {"name": "A2", "mux0": "gpio0", "mux1": "UART3_TX",
                 "mux2": "PWM0", "mux3": "sda0"}

class PinMuxBlockSingle(Elaboratable):

    def __init__(self, wb_wordsize, pinspec):
        print("1-bit Pin Mux Block with JTAG")
        self.n_ports = 4
        self.n_gpios = 1
        self.wb_wordsize = wb_wordsize # 4 Bytes, 32-bits

        # Create WB bus for the GPIO block
        class Spec: pass
        spec = Spec()
        spec.addr_wid = 30
        spec.mask_wid = 4
        spec.reg_wid = self.wb_wordsize*8

        temp = []
        for i in range(1, self.n_ports):
            temp_str = "%s" % (pinspec["mux%d" % i])
            temp.append(Record(name=temp_str, layout=io_layout))
        self.periph_ports = Array(temp)

        self.pad_port = Record(name=pinspec["name"], layout=io_layout)

        self.iomux = IOMuxBlockSingle(self.n_ports)
        self.gpio = SimpleGPIO(self.wb_wordsize, self.n_gpios)
        # This is probably easier to extend in future by bringing out WB
        # interface to top-level
        self.bus = self.gpio.bus

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync
        iomux = self.iomux
        gpio = self.gpio
        bus = self.bus
        periph_ports = self.periph_ports
        pad_port = self.pad_port

        # Add blocks to submodules
        m.submodules.iomux = iomux
        m.submodules.gpio = gpio

        # Connect up modules and signals
        # WB bus connection
        #m.d.comb += [gpio.bus.adr.eq(bus.adr),
        #             gpio.bus.dat_w.eq(bus.dat_w),
        #             bus.dat_r.eq(gpio.bus.dat_r),
        #             gpio.bus.sel.eq(bus.sel),
        #             gpio.bus.cyc.eq(bus.cyc),
        #             gpio.bus.stb.eq(bus.stb),
        #             bus.ack.eq(gpio.bus.ack),
        #             gpio.bus.we.eq(bus.we),
        #             bus.err.eq(gpio.bus.err),
        #             gpio.bus.cti.eq(bus.cti), # Cycle Type Identifier
        #             gpio.bus.bte.eq(bus.bte) # Burst Type Extension
        #            ]

        m.d.comb += iomux.port.eq(gpio.gpio_ports[0].bank)

        # WB GPIO always port0
        m.d.comb += iomux.periph_ports[0].o.eq(gpio.gpio_ports[0].o)
        m.d.comb += iomux.periph_ports[0].oe.eq(gpio.gpio_ports[0].oe)
        m.d.comb += gpio.gpio_ports[0].i.eq(iomux.periph_ports[0].i)

        # ports1-3 external
        for port in range(0, self.n_ports-1):
            m.d.comb += iomux.periph_ports[port+1].o.eq(periph_ports[port].o)
            m.d.comb += iomux.periph_ports[port+1].oe.eq(periph_ports[port].oe)
            m.d.comb += periph_ports[port].i.eq(iomux.periph_ports[port+1].i)

        m.d.comb += pad_port.o.eq(iomux.out_port.o)
        m.d.comb += pad_port.oe.eq(iomux.out_port.oe)
        m.d.comb += iomux.out_port.i.eq(pad_port.i)

        return m

    def __iter__(self):
        """ Get member signals for Verilog form. """
        for field in self.pad_port.fields.values():
            yield field
        for field in self.bus.fields.values():
            yield field
        for port in range(len(self.periph_ports)):
            for field in self.periph_ports[port].fields.values():
                yield field

    def ports(self):
        return list(self)

def gen_gtkw_doc(module_name, wordsize, n_ports, filename, pinspec):
    # GTKWave doc generation
    style = {
        '': {'base': 'hex'},
        'in': {'color': 'orange'},
        'out': {'color': 'yellow'},
        'debug': {'module': 'top', 'color': 'red'}
    }

    # Create a trace list, each block expected to be a tuple()
    traces = []
    wb_data_width = wordsize*8
    wb_traces = ('Wishbone Bus', [
                        ('gpio_wb__cyc', 'in'),
                        ('gpio_wb__stb', 'in'),
                        ('gpio_wb__we', 'in'),
                        ('gpio_wb__adr[27:0]', 'in'),
                        ('gpio_wb__dat_w[%d:0]' % (wb_data_width-1), 'in'),
                        ('gpio_wb__dat_r[%d:0]' % (wb_data_width-1), 'out'),
                        ('gpio_wb__ack', 'out'),
                ])
    traces.append(wb_traces)

    for port in range(0, n_ports):
        temp_traces = ('mux%d' % port, [
                        ('%s__i' % (pinspec["mux%d" % port]), 'in'),
                        ('%s__o' % (pinspec["mux%d" % port]), 'in'),
                        ('%s__oe' % (pinspec["mux%d" % port]), 'in')
                      ])
        traces.append(temp_traces)

    temp_traces = ('Misc', [
                    ('port[%d:0]' % ((n_ports-1).bit_length()-1), 'in')
                  ])
    traces.append(temp_traces)
    temp_traces = ('IO port to pad named: %s' % pinspec["name"], [
                    ('%s__i' % pinspec["name"], 'in'),
                    ('%s__o' % pinspec["name"], 'in'),
                    ('%s__oe' % pinspec["name"], 'in')
                  ])
    traces.append(temp_traces)
    #print(traces)

    write_gtkw(filename+".gtkw", filename+".vcd", traces, style,
               module=module_name)

def sim_iomux():
    filename = "test_gpio_pinmux" # Doesn't include extension
    wb_wordsize = 4

    dut = PinMuxBlockSingle(wb_wordsize, dummy_pinspec)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open(filename+".il", "w") as f:
        f.write(vl)

    print("Bus dir:")
    print(dut.bus.adr)
    print(dut.bus.fields)

    m = Module()
    m.submodules.pinmux = dut

    sim = Simulator(m)
    sim.add_clock(1e-6)

    sim.add_sync_process(wrap(test_gpio_pinmux(dut)))
    sim_writer = sim.write_vcd(filename+".vcd")
    with sim_writer:
        sim.run()

    gen_gtkw_doc("top.pinmux", wb_wordsize, dut.n_ports, filename,
                 dummy_pinspec)

def test_gpio_pinmux(dut):
    print("------START----------------------")
    #print(dir(dut.periph_ports[0]))
    #print(dut.periph_ports[0].fields)

    gpios = GPIOManager(dut.gpio, csrbus_layout, dut.bus)

    oe = 1
    ie = 0
    puen = 0
    pden = 1
    outval = 0
    port = 0
    yield from gpios.config("0", oe=1, ie=0, puen=0, pden=1, outval=0, bank=0)

    yield from gpios.set_out("0", outval=1)

    yield from gpios.config("0", oe=1, ie=0, puen=0, pden=1, outval=0, bank=2)

    yield dut.periph_ports[2].o.eq(1)
    yield
    yield dut.periph_ports[2].oe.eq(1)
    yield
    yield dut.pad_port.i.eq(1)
    yield
    yield dut.pad_port.i.eq(0)



    yield dut.pad_port.i.eq(1)
    yield
    yield from gpios.config("0", oe=0, ie=1, puen=0, pden=1, outval=0, bank=0)
    yield from gpios.rd_input("0")

    print("Finished the 1-bit IO mux block test!")

if __name__ == '__main__':
    sim_iomux()

