"""Simple GPIO peripheral on wishbone

This is an extremely simple GPIO peripheral intended for use in XICS
testing, however it could also be used as an actual GPIO peripheral

Modified for use with pinmux, will probably change the class name later.
"""
from random import randint
from math import ceil, floor
from nmigen import Elaboratable, Module, Signal, Record, Array, Cat
from nmigen.hdl.rec import Layout
from nmigen.utils import log2_int
from nmigen.cli import rtlil
from soc.minerva.wishbone import make_wb_layout
from nmutil.util import wrap
from soc.bus.test.wb_rw import wb_read, wb_write

from nmutil.gtkw import write_gtkw

cxxsim = False
if cxxsim:
    from nmigen.sim.cxxsim import Simulator, Settle
else:
    from nmigen.sim import Simulator, Settle

io_layout = (("i", 1),
             ("oe", 1),
             ("o", 1)
            )

class IOMuxBlock(Elaboratable):

    def __init__(self):
        print("IO Mux Block")
        self.n_banks = 4
        self.bank = Signal(log2_int(self.n_banks))

        temp = []
        for i in range(self.n_banks):
            temp_str = "bank{}".format(i)
            temp.append(Record(name=temp_str, layout=io_layout))
        self.bank_ports = Array(temp)

        self.out_port = Record(name="IO", layout=io_layout)

        #self.b0 = Record(name="b0", layout=io_layout)
        #self.b1 = Record(name="b1", layout=io_layout)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync

        bank = self.bank
        bank_ports = self.bank_ports
        #b0 = self.b0
        #b1 = self.b1
        out_port = self.out_port

        sync += out_port.o.eq(bank_ports[0].o)
        sync += out_port.oe.eq(bank_ports[0].oe)
        sync += bank_ports[0].i.eq(out_port.i)

        # Connect IO Pad output port to one of the peripheral IOs
        # Connect peripheral inputs to the IO pad input

        bank_range = range(self.n_banks)

        #with m.Switch(bank):

        for cur_bank in bank_range:
            sync += out_port.o.eq(bank_ports[cur_bank].o)
            sync += out_port.oe.eq(bank_ports[cur_bank].oe)
            sync += bank_ports[cur_bank].i.eq(out_port.i)

            temp_list = list(bank_range)
            temp_list.pop(temp_list.index(cur_bank))
            print("Banks with input hardwired to zero: {}".format(temp_list))
            for j in range(len(temp_list)):
                unused_bank = temp_list[j]
                sync += bank_ports[unused_bank].i.eq(0)

        return m

    def __iter__(self):
        """ Get member signals for Verilog form. """
        for field in self.out_port.fields.values():
            yield field
        for bank in range(len(self.bank_ports)):
            for field in self.bank_ports[bank].fields.values():
                yield field
        yield self.bank

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
    #print(traces)

    write_gtkw(filename+".gtkw", filename+".vcd", traces, style,
               module=module_name)

def sim_iomux():
    filename = "test_pinmux" # Doesn't include extension
    dut = IOMuxBlock()
    vl = rtlil.convert(dut, ports=dut.ports())
    with open(filename+".il", "w") as f:
        f.write(vl)

    m = Module()
    m.submodules.pinmux = dut

    sim = Simulator(m)
    sim.add_clock(1e-6)

    sim.add_sync_process(wrap(test_iomux(dut)))
    sim_writer = sim.write_vcd(filename+".vcd")
    with sim_writer:
        sim.run()

    gen_gtkw_doc("top.pinmux", dut.n_banks, filename)

def test_iomux(dut):
    print("------START----------------------")
    #print(dir(dut.bank_ports[0]))
    #print(dut.bank_ports[0].fields)
    #for (name, signal) in dut.b0.fields.items():
    #    print(name, signal)
    #print(dir(dut.bank_ports))
    #print(dut.bank_ports.__len__())
    #for bank in range(len(dut.bank_ports)):
    #    for values in dut.bank_ports[bank].fields.values():
    #        print(values)
    yield dut.bank_ports[0].o.eq(1)
    yield dut.bank.eq(0)
    yield
    yield dut.bank_ports[0].o.eq(1)
    yield
    yield
    yield dut.bank_ports[1].o.eq(1)
    yield
    yield dut.bank_ports[0].oe.eq(1)
    yield
    yield dut.bank.eq(1)
    yield

    yield dut.bank_ports[0].o.eq(0)
    yield
    yield dut.bank_ports[1].o.eq(0)
    yield
    yield dut.bank_ports[1].oe.eq(1)
    yield
    yield dut.bank.eq(0)
    yield

    print("Finished the IO mux block test!")

if __name__ == '__main__':
    sim_iomux()

