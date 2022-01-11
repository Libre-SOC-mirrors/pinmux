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
    from nmigen.sim import Simulator, Settle

# Bit shift position for CSR word used in WB transactions
IADDRSHIFT = 8 # offset needed to tell WB to return input ONLY
# Layout of 16-bit configuration word (? is unused):
# ? ? ? i | bank_select[3:0] |? pden puen opendrain |? ien oe o
ISHIFT = 12
BANKSHIFT = 8
# Pull-up/down, open-drain, ien have been skipped for now
OESHIFT = 1
OSHIFT = 0

class SimpleGPIO(Elaboratable):

    def __init__(self, n_gpio=16):
        self.n_gpio = n_gpio
        class Spec: pass
        spec = Spec()
        spec.addr_wid = 30
        spec.mask_wid = 4
        spec.reg_wid = 32
        self.bus = Record(make_wb_layout(spec), name="gpio_wb")
        # ONLY ONE BANK FOR ALL GPIOs atm...
        self.bank_sel = Signal(4) # set maximum number of banks to 16
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
        gpio_o_list = Array(list(gpio_o))
        print(bank_sel)
        print(gpio_o_list)
        gpio_oe_list = Array(list(gpio_oe))
        gpio_i_list = Array(list(gpio_i))

        # Address first byte for GPIO (max would be 256 GPIOs)
        # Address second byte, bit 0 indicates input read 
        with m.If(bus.cyc & bus.stb):
            comb += wb_ack.eq(1) # always ack
            comb += gpio_addr.eq(bus.adr[0:8])
            with m.If(bus.we): # write
                # Write to CSR
                sync += gpio_o_list[gpio_addr].eq(wb_wr_data[OSHIFT])
                sync += gpio_oe_list[gpio_addr].eq(wb_wr_data[OESHIFT])
                sync += bank_sel.eq(wb_wr_data[BANKSHIFT:BANKSHIFT+4])
            with m.Else(): # read
                # Read the value of the input
                with m.If(bus.adr[8]):
                    comb += wb_rd_data.eq(gpio_i_list[gpio_addr])
                # Read the state of CSR bits
                with m.Else():
                    comb += wb_rd_data.eq((gpio_o_list[gpio_addr] << OSHIFT)
                                          + (gpio_oe_list[gpio_addr] << OESHIFT)
                                          + (bank_sel << BANKSHIFT))
                #comb += wb_rd_data.eq(gpio_a[gpio_addr])

        return m

    def __iter__(self):
        for field in self.bus.fields.values():
            yield field
        yield self.gpio_o

    def ports(self):
        return list(self)



def gpio_configure(dut, gpio, oe, output=0, bank_sel=0):
    csr_val = ( (bank_sel << BANKSHIFT)
              | (oe << OESHIFT)
              | (output << OSHIFT) )
              # | (PUEN, PDUN, Open-drain etc...)
    print("Configuring CSR to {0:x}".format(csr_val))
    yield from wb_write(dut.bus, gpio, csr_val)

def gpio_rd_csr(dut, gpio):
    csr_val = yield from wb_read(dut.bus, gpio)
    print("GPIO{0} | CSR: {1:x}".format(gpio, csr_val))
    # gpio_parse_csr(csr_val)
    return data

def gpio_rd_input(dut, gpio):
    in_val = yield from wb_read(dut.bus, gpio | (1<<IADDRSHIFT))
    print("GPIO{0} | Input: {1:b}".format(gpio, in_val))
    return data

def gpio_set_out(dut, gpio, output):
    yield from wb_write(dut.bus, gpio, (output << OSHIFT))

def gpio_set_in_pad(dut, gpio, in_val):
    yield dut.gpio_i.eq(in_val)


def sim_gpio(dut):

    # GPIO0
    #data = yield from read_gpio(gpio, 0) # read gpio addr  0
    #yield from wb_write(gpio.bus, 0, 1) # write gpio addr 0
    #data = yield from read_gpio(gpio, 0) # read gpio addr  0
    print(dir(dut))
    print(dut)
    num_gpios = len(dut.gpio_o)
    bank_sel = 3
    oe = 1
    output = 0
    for gpio in range(0, num_gpios):
        yield from gpio_configure(dut, gpio, oe, output, bank_sel)
    
    for gpio in range(0, num_gpios):
        yield from gpio_set_out(dut, gpio, 1)

    #for gpio in range(0, num_gpios):
    #    yield from gpio_set_in_pad(dut, gpio, 1)
    yield from gpio_set_in_pad(dut, 0, 1)
    yield
    yield from gpio_set_in_pad(dut, 1, 1)
    yield
    yield from gpio_set_in_pad(dut, 2, 1)
    yield
    yield from gpio_set_in_pad(dut, 3, 1)
    yield
    yield from gpio_set_in_pad(dut, 2, 0)
    yield

    print("Finished the simple GPIO block test!")

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

