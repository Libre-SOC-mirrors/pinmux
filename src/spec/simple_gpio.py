"""Simple GPIO peripheral on wishbone

This is an extremely simple GPIO peripheral intended for use in XICS
testing, however it could also be used as an actual GPIO peripheral

Modified for use with pinmux, will probably change the class name later.
"""
from random import randint
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

# Layout of 8-bit configuration word:
# bank_select[2:0] i/o | pden puen ien oe
OESHIFT = 0
IESHIFT = 1
PUSHIFT = 2
PDSHIFT = 3
IOSHIFT = 4
BANKSHIFT = 5
NUM_BANKSEL_BITS = 3 # only supporting 8 banks (0-7)

# For future testing:
WORDSIZE = 8 # in bytes

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
        self.bank_sel = [Signal(NUM_BANKSEL_BITS)] * n_gpio
        self.gpio_o = Signal(n_gpio)
        self.gpio_oe = Signal(n_gpio)
        self.gpio_i = Signal(n_gpio)
        self.gpio_ie = Signal(n_gpio)
        self.pden = Signal(n_gpio)
        self.puen = Signal(n_gpio)

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
        gpio_ie = self.gpio_ie
        pden = self.pden
        puen = self.puen

        comb += wb_ack.eq(0)

        #for i in range(0, self.n_gpio):
        #    bank_sel[i]
        gpio_addr = Signal(log2_int(self.n_gpio))
        gpio_o_list = Array(list(gpio_o))
        print(bank_sel)
        print(gpio_o_list)
        gpio_oe_list = Array(list(gpio_oe))
        gpio_i_list = Array(list(gpio_i))
        gpio_ie_list = Array(list(gpio_ie))
        pden_list = Array(list(pden))
        puen_list = Array(list(puen))

        # One address used to configure CSR, set output, read input
        with m.If(bus.cyc & bus.stb):
            comb += wb_ack.eq(1) # always ack
            comb += gpio_addr.eq(bus.adr)
            with m.If(bus.we): # write
                # Write/set output
                sync += gpio_oe_list[gpio_addr].eq(wb_wr_data[OESHIFT])
                sync += gpio_ie_list[gpio_addr].eq(wb_wr_data[IESHIFT])
                # check GPIO is in output mode and NOT input (oe high, ie low)
                with m.If(wb_wr_data[OESHIFT] & (~wb_wr_data[IESHIFT])):
                    sync += gpio_o_list[gpio_addr].eq(wb_wr_data[IOSHIFT])
                sync += puen_list[gpio_addr].eq(wb_wr_data[PUSHIFT])
                sync += pden_list[gpio_addr].eq(wb_wr_data[PDSHIFT])
                # TODO: clean up name
                sync += bank_sel[gpio_addr].eq(
                        wb_wr_data[BANKSHIFT:BANKSHIFT+NUM_BANKSEL_BITS])
            with m.Else(): # read
                # Read the state of CSR bits
                with m.Else():
                    comb += wb_rd_data.eq((gpio_oe_list[gpio_addr] << OESHIFT)
                                          + (gpio_ie_list[gpio_addr] << IESHIFT)
                                          + (puen_list[gpio_addr] << PUSHIFT)
                                          + (pden_list[gpio_addr] << PDSHIFT)
                                          + (gpio_i_list[gpio_addr] << IOSHIFT)
                                          + (bank_sel << BANKSHIFT))
        return m

    def __iter__(self):
        for field in self.bus.fields.values():
            yield field
        yield self.gpio_o

    def ports(self):
        return list(self)

# TODO: probably make into class (or return state in a variable) 
def gpio_configure(dut, gpio, oe, ie, pden, puen, bank_sel=0):
    csr_val = ( (bank_sel << BANKSHIFT)
              | (pden << PDSHIFT)
              | (puen << PUSHIFT)
              | (oe << OESHIFT)
              | (ie << IESHIFT) )
    print("Configuring CSR to {0:x}".format(csr_val))
    yield from wb_write(dut.bus, gpio, csr_val)

# TODO: Return the configuration states
def gpio_rd_csr(dut, gpio):
    csr_val = yield from wb_read(dut.bus, gpio)
    print("GPIO{0} | CSR: {1:x}".format(gpio, csr_val))
    # gpio_parse_csr(csr_val)
    return data

# TODO
def gpio_rd_input(dut, gpio):
    in_val = yield from wb_read(dut.bus, gpio | (IADDR<<ADDROFFSET))
    print("GPIO{0} | Input: {1:b}".format(gpio, in_val))
    return data

def gpio_set_out(dut, gpio, output):
    yield from wb_write(dut.bus, gpio | (OADDR<<ADDROFFSET), (output<<OSHIFT))

# TODO: There's probably a cleaner way to clear the bit...
def gpio_set_in_pad(dut, gpio, in_val):
    old_in_val = yield dut.gpio_i
    if in_val:
        new_in_val = old_in_val | (in_val << gpio)
    else:
        temp = (old_in_val >> gpio) & 1
        if temp:
            mask = ~(1 << gpio)
            new_in_val = old_in_val & mask
        else:
            new_in_val = old_in_val
    print("Previous GPIO i: {0:b} | New GPIO i: {1:b}"
          .format(old_in_val, new_in_val))
    yield dut.gpio_i.eq(new_in_val)

def sim_gpio(dut, use_random=True):

    # GPIO0
    #data = yield from read_gpio(gpio, 0) # read gpio addr  0
    #yield from wb_write(gpio.bus, 0, 1) # write gpio addr 0
    #data = yield from read_gpio(gpio, 0) # read gpio addr  0
    print(dir(dut))
    print(dut)
    num_gpios = len(dut.gpio_o)
    if use_random:
        bank_sel = randint(0, num_gpios)
    else:
        bank_sel = 3 # not special, chose for testing
    oe = 1
    output = 0
    # Configure GPIOs for 
    for gpio in range(0, num_gpios):
        yield from gpio_configure(dut, gpio, oe, output, bank_sel)
    
    for gpio in range(0, num_gpios):
        yield from gpio_set_out(dut, gpio, 1)

    for gpio in range(0, num_gpios):
        yield from gpio_set_in_pad(dut, gpio, 1)
        yield

    for gpio in range(0, num_gpios):
        yield from gpio_set_in_pad(dut, gpio, 0)
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

