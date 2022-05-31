"""Simple GPIO peripheral on wishbone

This is an extremely simple GPIO peripheral intended for use in XICS
testing, however it could also be used as an actual GPIO peripheral

Modified for use with pinmux, will probably change the class name later.
"""
from random import randint, shuffle
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

io_layout = (("i", 1),
             ("oe", 1),
             ("o", 1)
            )

class IOMuxBlockSingle(Elaboratable):

    def __init__(self, n_banks=4):
        print("1-bit IO Mux Block")
        self.n_banks = n_banks
        self.bank = Signal(log2_int(self.n_banks))

        temp = []
        for i in range(self.n_banks):
            name = "bank%d" % i
            temp.append(Record(name=name, layout=io_layout))
        self.bank_ports = Array(temp)

        self.out_port = Record(name="IO", layout=io_layout)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync

        bank = self.bank
        bank_ports = self.bank_ports
        out_port = self.out_port

        # Connect IO Pad output port to one of the peripheral IOs
        # Connect peripheral inputs to the IO pad input
        comb += self.out_port.o.eq(self.bank_ports[bank].o)
        comb += self.out_port.oe.eq(self.bank_ports[bank].oe)

        comb += self.bank_ports[bank].i.eq(self.out_port.i)

        return m

    def connect_bank_to_io(self, domain, bank_arg):
        domain += self.out_port.o.eq(self.bank_ports[bank_arg].o)
        domain += self.out_port.oe.eq(self.bank_ports[bank_arg].oe)
        domain += self.bank_ports[bank_arg].i.eq(self.out_port.i)

    def __iter__(self):
        """ Get member signals for Verilog form. """
        for field in self.out_port.fields.values():
            yield field
        for bank in range(self.n_banks):
            for field in self.bank_ports[bank].fields.values():
                yield field
        yield self.bank

    def ports(self):
        return list(self)

# Method to test a particular bank port
# when rand_order is True, previous and consecutive banks are
# random (but NOT equal to given bank)
def test_single_bank(dut, bank, rand_order=True, delay=1e-6):
    if rand_order:
        print("Randomising the prev and next banks")
        prev_bank=bank
        while(prev_bank == bank):
            prev_bank = randint(0, dut.n_banks-1)
        next_bank=bank
        while(next_bank == bank):
            next_bank = randint(0, dut.n_banks-1)
    else:
        # Set the prev and next banks as consecutive banks
        if bank == 0:
            prev_bank = dut.n_banks - 1
        else:
            prev_bank = bank - 1

        if bank == dut.n_banks:
            next_bank = 0
        else:
            next_bank = bank + 1

    print("Prev=%d, Given=%d, Next=%d" % (prev_bank, bank, next_bank))

    # Clear o/oe, delay, set port i
    # Set to previous bank, delay
    # Assert bank i == 0
    # Set to desired bank
    # Assert bank i == 1
    # Set o/oe, delay
    # Assert o, oe == 1
    # Set to next bank, delay
    # Assert bank i == 0
    yield dut.bank_ports[bank].o.eq(0)
    yield Delay(delay)
    yield dut.bank_ports[bank].oe.eq(0)
    yield Delay(delay)
    yield dut.out_port.i.eq(1)
    yield Delay(delay)

    yield dut.bank.eq(prev_bank)
    yield Delay(delay)

    test_i = yield dut.bank_ports[bank].i
    assert(test_i == 0)

    yield dut.bank.eq(bank)
    yield Delay(delay)

    test_o = yield dut.out_port.o
    test_oe = yield dut.out_port.oe
    test_i = yield dut.bank_ports[bank].i
    assert(test_o == 0)
    assert(test_oe == 0)
    assert(test_i == 1)

    yield dut.bank_ports[bank].o.eq(1)
    yield Delay(delay)
    yield dut.bank_ports[bank].oe.eq(1)
    yield Delay(delay)

    test_o = yield dut.out_port.o
    test_oe = yield dut.out_port.oe
    assert(test_o == 1)
    assert(test_oe == 1)

    yield dut.bank.eq(next_bank)
    yield Delay(delay)

    test_i = yield dut.bank_ports[bank].i
    assert(test_i == 0)

def test_iomux(dut, rand_order=True):
    print("------START----------------------")
    #print(dir(dut.bank_ports[0]))
    #print(dut.bank_ports[0].fields)

    # Produce a test list of bank values
    test_bank_vec = list(range(0, dut.n_banks))
    #print(test_bank_vec)
    # Randomise for wider testing
    if rand_order:
        shuffle(test_bank_vec)
        #print(test_bank_vec)
    for i in range(dut.n_banks):
        yield from test_single_bank(dut, test_bank_vec[i], rand_order)

    print("Finished the 1-bit IO mux block test!")

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
        temp_traces = ('Bank%d' % bank, [
                        ('bank%d__i' % bank, 'in'),
                        ('bank%d__o' % bank, 'out'),
                        ('bank%d__oe' % bank, 'out')
                      ])
        traces.append(temp_traces)

    temp_traces = ('Misc', [
                    ('bank[%d:0]' % ((n_banks-1).bit_length()-1), 'in')
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

def sim_iomux(rand_order=True):
    filename = "test_iomux" # Doesn't include extension
    n_banks = 8
    dut = IOMuxBlockSingle(n_banks)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open(filename+".il", "w") as f:
        f.write(vl)

    m = Module()
    m.submodules.pinmux = dut

    sim = Simulator(m)

    sim.add_process(wrap(test_iomux(dut, rand_order)))
    sim_writer = sim.write_vcd(filename+".vcd")
    with sim_writer:
        sim.run()

    gen_gtkw_doc("top.pinmux", dut.n_banks, filename)



if __name__ == '__main__':
    sim_iomux(rand_order=True)

