"""
1-bit pinmux case

"""
from random import randint
#from math import ceil, floor
from nmigen import Elaboratable, Module, Signal, Record, Array, Cat
from nmigen.hdl.rec import Layout
from nmigen.utils import log2_int
from nmigen.cli import rtlil
#from soc.minerva.wishbone import make_wb_layout
from nmutil.util import wrap
#from soc.bus.test.wb_rw import wb_read, wb_write

from nmutil.gtkw import write_gtkw

cxxsim = False
if cxxsim:
    from nmigen.sim.cxxsim import Simulator, Settle, Delay
else:
    from nmigen.sim import Simulator, Settle, Delay

from iomux import IOMuxBlockSingle, io_layout
from simple_gpio import SimpleGPIO

class PinMuxBlockSingle(Elaboratable):

    def __init__(self):
        print("1-bit Pin Mux Block with JTAG")
        self.n_banks = 4
        self.bank = Signal(log2_int(self.n_banks))
        self.n_gpios = 1
        self.wb_wordsize = 4 # 4 Bytes, 32-bits

        temp = []
        for i in range(1, self.n_banks):
            temp_str = "periph{}".format(i)
            temp.append(Record(name=temp_str, layout=io_layout))
        self.periph_ports = Array(temp)

        self.out_port = Record(name="IO", layout=io_layout)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync
        iomux = IOMuxBlockSingle()
        gpio = SimpleGPIO(self.wb_wordsize, self.n_gpios)
        m.submodules.iomux += iomux
        m.submodules.gpio += gpio

        bank = self.bank
        periph_ports = self.periph_ports
        out_port = self.out_port

        # Connect up modules and signals
        iomux.bank.eq(gpio.gpio_ports[0].bank)

        # WB GPIO always bank0
        gpio.gpio_ports[0].o.eq(iomux.bank_ports[0].o)
        gpio.gpio_ports[0].oe.eq(iomux.bank_ports[0].oe)
        iomux.bank_ports[0].i.eq(gpio.gpio_ports[0].i)

        # banks1-3 external
        for bank in range(0, self.n_banks-1):
            periph_ports[bank].o.eq(iomux.bank_ports[bank+1].o)
            periph_ports[bank].oe.eq(iomux.bank_ports[bank+1].oe)
            iomux.bank_ports[bank+1].i.eq(periph_ports[bank].i)

        out_port.o.eq(iomux.out_port.o)
        out_port.oe.eq(iomux.out_port.oe)
        iomux.out_port.i.eq(out_port.i)

        return m

    def __iter__(self):
        """ Get member signals for Verilog form. """
        for field in self.out_port.fields.values():
            yield field
        for bank in range(len(self.periph_ports)):
            for field in self.periph_ports[bank].fields.values():
                yield field
        #yield self.bank

    def ports(self):
        return list(self)

def gen_gtkw_doc(module_name, n_banks, filename):
    # GTKWave doc generation
    style = {
        '': {'base': 'hex'},
        'in': {'color': 'orange'},
        'out': {'color': 'yellow'},
        'debug': {'module': 'top', 'color': 'red'}
    }

    # Create a trace list, each block expected to be a tuple()
    traces = []
    for bank in range(0, n_banks):
        temp_traces = ('Bank{}'.format(bank), [
                        ('bank{}__i'.format(bank), 'in'),
                        ('bank{}__o'.format(bank), 'out'),
                        ('bank{}__oe'.format(bank), 'out')
                      ])
        traces.append(temp_traces)

    temp_traces = ('Misc', [
                    ('bank[1:0]', 'in')
                  ])
    traces.append(temp_traces)
    temp_traces = ('IO port to pad', [
                    ('IO__i', 'in'),
                    ('IO__o', 'out'),
                    ('IO__oe', 'out')
                  ])
    traces.append(temp_traces)
    #print(traces)

    write_gtkw(filename+".gtkw", filename+".vcd", traces, style,
               module=module_name)

def sim_iomux():
    filename = "test_pinmux" # Doesn't include extension
    dut = PinMuxBlockSingle()
    vl = rtlil.convert(dut, ports=dut.ports())
    with open(filename+".il", "w") as f:
        f.write(vl)

    #m = Module()
    #m.submodules.pinmux = dut

    #sim = Simulator(m)

    #sim.add_process(wrap(test_iomux(dut)))
    #sim_writer = sim.write_vcd(filename+".vcd")
    #with sim_writer:
    #    sim.run()

    #gen_gtkw_doc("top.pinmux", dut.n_banks, filename)

def test_iomux(dut):
    print("------START----------------------")
    #print(dir(dut.bank_ports[0]))
    #print(dut.bank_ports[0].fields)

    # TODO: turn into methods
    yield from test_single_bank(dut, 0)
    yield from test_single_bank(dut, 1)
    yield from test_single_bank(dut, 2)
    yield from test_single_bank(dut, 3)

    print("Finished the 1-bit IO mux block test!")

if __name__ == '__main__':
    sim_iomux()

