"""This is the module used for multiplexing IO signals

Documentation: https://libre-soc.org/docs/pinmux/temp_pinmux_info/
Bug: https://bugs.libre-soc.org/show_bug.cgi?id=762
"""
#from random import randint
from nmigen import Elaboratable, Module, Signal, Record, Array
#from nmigen.utils import log2_int
from nmigen.cli import rtlil
#from soc.minerva.wishbone import make_wb_layout
from nmutil.util import wrap
#from soc.bus.test.wb_rw import wb_read, wb_write

cxxsim = False
if cxxsim:
    from nmigen.sim.cxxsim import Simulator, Settle
else:
    from nmigen.sim import Simulator, Settle

class IOMuxBlock(Elaboratable):

    def __init__(self):
        self.bank_sel = Signal()
        
        self.portin0 = {"i": Signal(), "o": Signal(), "oe": Signal()}
        self.portin1 = {"i": Signal(), "o": Signal(), "oe": Signal()}
        self.portout = {"i": Signal(), "o": Signal(), "oe": Signal()}

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync
        
        bank_sel = self.bank_sel
        portin0 = self.portin0
        portin1 = self.portin1
        portout = self.portout
        # Connect IO Pad output port to one of the peripheral IOs
        comb += portout["o"].eq(Mux(bank_sel, portin1["o"], portin0["o"]))
        comb += portout["oe"].eq(Mux(bank_sel, portin1["oe"], portin0["oe"]))
        
        # Connect peripheral inputs to the IO pad input
        comb += portin0["i"].eq(Mux(bank_sel, 0, portout["i"]))
        comb += portin1["i"].eq(Mux(bank_sel, portout["i"], 0))

        return m

    def ports(self):
        return list(self)

def sim_iomux(dut):
    # start by setting portin0
    dut.portin0["o"].eq(1)
    dut.portin0["oe"].eq(1)
    yield
    dut.portout["i"].eq(1)
    
    print("Finished the IO mux block test!")

def test_iomux():

    dut = IOMuxBlock()
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_gpio.il", "w") as f:
        f.write(vl)

    m = Module()

    #sim = Simulator(m)
    #sim.add_clock(1e-6)

    #sim.add_sync_process(wrap(sim_gpio(dut)))
    #sim_writer = sim.write_vcd('test_gpio.vcd')
    #with sim_writer:
    #    sim.run()


if __name__ == '__main__':
    test_iomux()

