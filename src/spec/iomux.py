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

# This block produces an N-to-1 mux with N 3-bit periph ports and one pad port.
# The peripheral ports are intended to be wired to peripheral functions,
# while the pad port will connect to the I/O pad.
# Peripheral and output ports have o/oe/i signals, and the port signal is used
# to select between the peripheral ports.
class IOMuxBlockSingle(Elaboratable):

    def __init__(self, n_ports=4):
        print("1-bit IO Mux Block")
        self.n_ports = n_ports
        self.port = Signal(log2_int(self.n_ports))

        temp = []
        for i in range(self.n_ports):
            name = "port%d" % i
            temp.append(Record(name=name, layout=io_layout))
        self.periph_ports = Array(temp)

        self.out_port = Record(name="IO", layout=io_layout)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync

        port = self.port
        periph_ports = self.periph_ports
        out_port = self.out_port

        # Connect IO Pad output port to one of the peripheral IOs
        # Connect peripheral inputs to the IO pad input
        comb += self.out_port.o.eq(self.periph_ports[port].o)
        comb += self.out_port.oe.eq(self.periph_ports[port].oe)

        comb += self.periph_ports[port].i.eq(self.out_port.i)

        return m

    def connect_port_to_io(self, domain, port_arg):
        domain += self.out_port.o.eq(self.periph_ports[port_arg].o)
        domain += self.out_port.oe.eq(self.periph_ports[port_arg].oe)
        domain += self.periph_ports[port_arg].i.eq(self.out_port.i)

    def __iter__(self):
        """ Get member signals for Verilog form. """
        for field in self.out_port.fields.values():
            yield field
        for port in range(self.n_ports):
            for field in self.periph_ports[port].fields.values():
                yield field
        yield self.port

    def ports(self):
        return list(self)

# Method to test a particular peripheral port
# when rand_order is True, previous and consecutive ports are
# random (but NOT equal to given port)
def test_single_port(dut, port, rand_order=True, delay=1e-6):
    if rand_order:
        print("Randomising the prev and next ports")
        prev_port=port
        while(prev_port == port):
            prev_port = randint(0, dut.n_ports-1)
        next_port=port
        while(next_port == port):
            next_port = randint(0, dut.n_ports-1)
    else:
        # Set the prev and next ports as consecutive ports
        if port == 0:
            prev_port = dut.n_ports - 1
        else:
            prev_port = port - 1

        if port == dut.n_ports:
            next_port = 0
        else:
            next_port = port + 1

    print("Prev=%d, Given=%d, Next=%d" % (prev_port, port, next_port))

    # Clear o/oe, delay, set port i
    # Set to previous port, delay
    # Assert port i == 0
    # Set to desired port
    # Assert port i == 1
    # Set o/oe, delay
    # Assert o, oe == 1
    # Set to next port, delay
    # Assert port i == 0
    yield dut.periph_ports[port].o.eq(0)
    yield Delay(delay)
    yield dut.periph_ports[port].oe.eq(0)
    yield Delay(delay)
    yield dut.out_port.i.eq(1)
    yield Delay(delay)

    yield dut.port.eq(prev_port)
    yield Delay(delay)

    test_i = yield dut.periph_ports[port].i
    assert(test_i == 0)

    yield dut.port.eq(port)
    yield Delay(delay)

    test_o = yield dut.out_port.o
    test_oe = yield dut.out_port.oe
    test_i = yield dut.periph_ports[port].i
    assert(test_o == 0)
    assert(test_oe == 0)
    assert(test_i == 1)

    yield dut.periph_ports[port].o.eq(1)
    yield Delay(delay)
    yield dut.periph_ports[port].oe.eq(1)
    yield Delay(delay)

    test_o = yield dut.out_port.o
    test_oe = yield dut.out_port.oe
    assert(test_o == 1)
    assert(test_oe == 1)

    yield dut.port.eq(next_port)
    yield Delay(delay)

    test_i = yield dut.periph_ports[port].i
    assert(test_i == 0)

def test_iomux(dut, rand_order=True):
    print("------START----------------------")
    #print(dir(dut.periph_ports[0]))
    #print(dut.periph_ports[0].fields)

    # Produce a test list of port values
    test_port_vec = list(range(0, dut.n_ports))
    #print(test_port_vec)
    # Randomise for wider testing
    if rand_order:
        shuffle(test_port_vec)
        #print(test_port_vec)
    for i in range(dut.n_ports):
        yield from test_single_port(dut, test_port_vec[i], rand_order)

    print("Finished the 1-bit IO mux block test!")

def gen_gtkw_doc(module_name, n_ports, filename):
    # GTKWave doc generation
    style = {
        '': {'base': 'hex'},
        'in': {'color': 'orange'},
        'out': {'color': 'yellow'},
        'debug': {'module': 'top', 'color': 'red'}
    }

    # Create a trace list, each block expected to be a tuple()
    traces = []
    for port in range(0, n_ports):
        temp_traces = ('Bank%d' % port, [
                        ('port%d__i' % port, 'in'),
                        ('port%d__o' % port, 'out'),
                        ('port%d__oe' % port, 'out')
                      ])
        traces.append(temp_traces)

    temp_traces = ('Misc', [
                    ('port[%d:0]' % ((n_ports-1).bit_length()-1), 'in')
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
    n_ports = 8
    dut = IOMuxBlockSingle(n_ports)
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

    gen_gtkw_doc("top.pinmux", dut.n_ports, filename)



if __name__ == '__main__':
    sim_iomux(rand_order=True)

