"""Simple GPIO peripheral on wishbone

This is an extremely simple GPIO peripheral intended for use in XICS
testing, however it could also be used as an actual GPIO peripheral

Modified for use with pinmux, will probably change the class name later.
"""

from nmigen import Elaboratable, Module, Signal, Record, Array
from nmigen.utils import log2_int
from nmigen.cli import rtlil
from soc.minerva.wishbone import make_wb_layout
from nmutil.util import wrap
from soc.bus.test.wb_rw import wb_read, wb_write

cxxsim = False
if cxxsim:
    from nmigen.sim.cxxsim import Simulator, Settle
else:
    from nmigen.back.pysim import Simulator, Settle


class SimpleGPIO(Elaboratable):

    def __init__(self, n_gpio=16):
        self.n_gpio = n_gpio
        class Spec: pass
        spec = Spec()
        spec.addr_wid = 30
        spec.mask_wid = 4
        spec.reg_wid = 32
        self.bus = Record(make_wb_layout(spec), name="gpio_wb")
        self.bank_sel = Array([Signal(3) for _ in range(n_gpio)])
        self.gpio_o = Signal(n_gpio)
        self.gpio_oe = Signal(n_gpio)
        self.gpio_i = Signal(n_gpio)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync

        bus = self.bus
        wb_rd_data = bus.dat_r
        wb_wr_data = bus.dat_w
        wb_ack = bus.ack

        bank_sel = self.bank_sel
        gpio_o = self.gpio_o
        gpio_oe = self.gpio_oe
        gpio_i = self.gpio_i

        comb += wb_ack.eq(0)

        gpio_addr = Signal(log2_int(self.n_gpio))
        gpio_a = Array(list(gpio_o))
        bank_sel_list = Array(list(bank_sel))
        print(bank_sel)
        print(bank_sel_list)
        print(gpio_a)
        gpio_oe_list = Array(list(gpio_o))
        gpio_i_list = Array(list(gpio_i))

        # Address first byte for GPIO (max would be 256 GPIOs)
        # Address second byte, bit 0 indicates input read 
        with m.If(bus.cyc & bus.stb):
            comb += wb_ack.eq(1) # always ack
            comb += gpio_addr.eq(bus.adr[0:8])
            with m.If(bus.we): # write
                # Write to CSR - direction and bank select
                sync += gpio_a[gpio_addr].eq(wb_wr_data[0])
                sync += gpio_oe_list[gpio_addr].eq(wb_wr_data[1])
                sync += bank_sel_list[gpio_addr].eq(wb_wr_data[5:8])
            with m.Else(): # read
                # Read the value of the input
                with m.If(bus.adr[8]):
                    comb += wb_rd_data.eq(gpio_i_list[gpio_addr])
                # Read the state of CSR bits
                with m.Else():
                    comb += wb_rd_data.eq(gpio_o[gpio_addr] 
                                          + (gpio_oe[gpio_addr] << 1)
                                          + (bank_sel_list[gpio_addr] << 5))
                #comb += wb_rd_data.eq(gpio_a[gpio_addr])

        return m

    def __iter__(self):
        for field in self.bus.fields.values():
            yield field
        yield self.gpio_o

    def ports(self):
        return list(self)



def read_gpio(gpio, addr):
    data = yield from wb_read(gpio.bus, addr)
    print ("gpio%d" % addr, hex(data), bin(data))
    return data


def sim_gpio(gpio):

    # GPIO0
    data = yield from read_gpio(gpio, 0) # read gpio addr  0
    
    yield from wb_write(gpio.bus, 0, 1) # write gpio addr 0

    data = yield from read_gpio(gpio, 0) # read gpio addr  0

def test_gpio():

    dut = SimpleGPIO()
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_gpio.il", "w") as f:
        f.write(vl)

    m = Module()
    m.submodules.xics_icp = dut

    sim = Simulator(m)
    sim.add_clock(1e-6)

    sim.add_sync_process(wrap(sim_gpio(dut)))
    sim_writer = sim.write_vcd('test_gpio.vcd')
    with sim_writer:
        sim.run()


if __name__ == '__main__':
    test_gpio()

