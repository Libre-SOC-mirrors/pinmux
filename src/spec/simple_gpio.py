"""Simple GPIO peripheral on wishbone

This is an extremely simple GPIO peripheral intended for use in XICS
testing, however it could also be used as an actual GPIO peripheral

Modified for use with pinmux, will probably change the class name later.
"""
from random import randint
from nmigen import Elaboratable, Module, Signal, Record, Array
from nmigen.hdl.rec import Layout
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
NUMBANKBITS = 3 # only supporting 8 banks (0-7)

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

        self.bank_sel = Array([Signal(NUMBANKBITS) for _ in range(n_gpio)])
        self.gpio_o = Signal(n_gpio)
        self.gpio_oe = Signal(n_gpio)
        self.gpio_i = Signal(n_gpio)
        self.gpio_ie = Signal(n_gpio)
        self.pden = Signal(n_gpio)
        self.puen = Signal(n_gpio)

        layout = (("oe", 1),
                  ("ie", 1),
                  ("puen", 1),
                  ("pden", 1),
                  ("io", 1),
                  ("bank_sel", NUMBANKBITS)
                 )
        self.csrbus = Record(layout)

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
        csrbus = self.csrbus

        comb += wb_ack.eq(0)

        gpio_addr = Signal(log2_int(self.n_gpio))
        gpio_o_list = Array(list(gpio_o))
        print(bank_sel)
        print(gpio_o_list)
        gpio_oe_list = Array(list(gpio_oe))
        gpio_i_list = Array(list(gpio_i))
        gpio_ie_list = Array(list(gpio_ie))
        pden_list = Array(list(pden))
        puen_list = Array(list(puen))

        # Flag for indicating rd/wr transactions
        new_transaction = Signal(1)

        #print("Types:")
        #print("gpio_addr: ", type(gpio_addr))
        #print("gpio_o_list: ", type(gpio_o_list))
        #print("bank_sel: ", type(bank_sel))

        # One address used to configure CSR, set output, read input
        with m.If(bus.cyc & bus.stb):
            comb += wb_ack.eq(1) # always ack
            comb += gpio_addr.eq(bus.adr)

            sync += new_transaction.eq(1)
            with m.If(bus.we): # write
                # Configure CSR
                sync += csrbus.eq(wb_wr_data)
            with m.Else(): # read
                # Read the state of CSR bits
                comb += wb_rd_data.eq(csrbus)
        with m.Else():
            sync += new_transaction.eq(0)
            # Update the state of "io" while no WB transactions
            with m.If(gpio_oe_list[gpio_addr] & (~gpio_ie_list[gpio_addr])):
                sync += csrbus.io.eq(gpio_o_list[gpio_addr])
            with m.If(gpio_ie_list[gpio_addr] & (~gpio_oe_list[gpio_addr])):
                sync += csrbus.io.eq(gpio_i_list[gpio_addr])
            with m.Else():
                sync += csrbus.io.eq(csrbus.io)

        # Only update GPIOs config if a new transaction happened last cycle
        # (read or write). Always lags from csrbus by 1 clk cycle, most
        # sane way I could think of while using Record().
        with m.If(new_transaction):
            sync += gpio_oe_list[gpio_addr].eq(csrbus.oe)
            sync += gpio_ie_list[gpio_addr].eq(csrbus.ie)
            # Check to prevent output being set if GPIO configured as input
            # TODO: Is this necessary? PAD might deal with this
            # check GPIO is in output mode and NOT input (oe high, ie low)
            with m.If(gpio_oe_list[gpio_addr] & (~gpio_ie_list[gpio_addr])):
                sync += gpio_o_list[gpio_addr].eq(csrbus.io)
            sync += puen_list[gpio_addr].eq(csrbus.puen)
            sync += pden_list[gpio_addr].eq(csrbus.pden)
            sync += bank_sel[gpio_addr].eq(csrbus.bank_sel)
        return m

    def __iter__(self):
        for field in self.bus.fields.values():
            yield field
        yield self.gpio_o

    def ports(self):
        return list(self)

# TODO: probably make into class (or return state in a variable) 
def gpio_configure(dut, gpio, oe, ie, puen, pden, outval, bank_sel):
    csr_val = ( (oe   << OESHIFT)
              | (ie   << IESHIFT)
              | (puen << PUSHIFT)
              | (pden << PDSHIFT)
              | (bank_sel << BANKSHIFT) )
    print("Configuring CSR to {0:x}".format(csr_val))
    yield from wb_write(dut.bus, gpio, csr_val)
    yield # Allow one clk cycle to propagate

    return csr_val # return the config state

def reg_write(dut, gpio, reg_val):
    print("Configuring CSR to {0:x}".format(reg_val))
    yield from wb_write(dut.bus, gpio, reg_val)

# TODO: Return the configuration states
def gpio_rd_csr(dut, gpio):
    csr_val = yield from wb_read(dut.bus, gpio)
    print("GPIO{0} | CSR: {1:x}".format(gpio, csr_val))
    print("Output Enable: {0:b}".format((csr_val >> OESHIFT) & 1))
    print("Input Enable: {0:b}".format((csr_val >> IESHIFT) & 1))
    print("Pull-Up Enable: {0:b}".format((csr_val >> PUSHIFT) & 1))
    print("Pull-Down Enable: {0:b}".format((csr_val >> PDSHIFT) & 1))
    if ((csr_val >> IESHIFT) & 1):
        print("Input: {0:b}".format((csr_val >> IOSHIFT) & 1))
    else:
        print("Output: {0:b}".format((csr_val >> IOSHIFT) & 1))
    print("Bank Select: {0:b}".format((csr_val >> BANKSHIFT) & 1))
    # gpio_parse_csr(csr_val)
    return csr_val

# TODO
def gpio_rd_input(dut, gpio):
    in_val = yield from wb_read(dut.bus, gpio)
    in_val = (in_val >> IOSHIFT) & 1
    print("GPIO{0} | Input: {1:b}".format(gpio, in_val))
    return in_val

def gpio_set_out(dut, gpio, csr_val, output):
    print("Setting GPIO{0} output to {1}".format(gpio, output))
    yield from wb_write(dut.bus, gpio, csr_val | (output<<IOSHIFT))
    yield # Allow one clk cycle to propagate

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
    yield # Allow one clk cycle to propagate

def gpio_test_in_pattern(dut, pattern):
    num_gpios = len(dut.gpio_o)
    print("Test pattern:")
    print(pattern)
    for pat in range(0, len(pattern)):
        for gpio in range(0, num_gpios):
            yield from gpio_set_in_pad(dut, gpio, pattern[pat])
            yield
            temp = yield from gpio_rd_input(dut, gpio)
            print("Pattern: {0}, Reading {1}".format(pattern[pat], temp))
            assert (temp == pattern[pat])
            pat += 1
            if pat == len(pattern):
                break


def sim_gpio(dut, use_random=True):
    print(dir(dut))
    print(dut)
    num_gpios = len(dut.gpio_o)
    if use_random:
        bank_sel = randint(0, 2**NUMBANKBITS)
        print("Random bank_select: {0:b}".format(bank_sel))
    else:
        bank_sel = 3 # not special, chose for testing
    oe = 1
    ie = 0
    output = 0
    puen = 0 # 1
    pden = 0
    gpio_csr = [0] * num_gpios
    # Configure GPIOs for 
    for gpio in range(0, num_gpios):
        gpio_csr[gpio] = yield from gpio_configure(dut, gpio, oe, ie, puen, 
                                                   pden, output, bank_sel)
    # Set outputs
    for gpio in range(0, num_gpios):
        yield from gpio_set_out(dut, gpio, gpio_csr[gpio], 1)

    # Read CSR
    for gpio in range(0, num_gpios):
        yield from gpio_rd_csr(dut, gpio)

    # Configure for input
    oe = 0
    ie = 1
    #for gpio in range(0, num_gpios):
    #    gpio_csr[gpio] = yield from gpio_configure(dut, gpio, oe, ie, puen, 
    #                                               pden, output, bank_sel)
    # Input testing
    #    temp = yield from gpio_rd_input(dut, gpio)
    #    yield from gpio_set_in_pad(dut, gpio, 1)
    #    temp = yield from gpio_rd_input(dut, gpio)

    # TODO: not working yet
    #test_pattern = []
    #for i in range(0, (num_gpios * 2)):
    #    test_pattern.append(randint(0,1))
    #yield from gpio_test_in_pattern(dut, test_pattern)

    #reg_val = 0x32
    #yield from reg_write(dut, 0, reg_val)
    #yield from reg_write(dut, 0, reg_val)
    #yield
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

    sim.add_sync_process(wrap(sim_gpio(dut, use_random=False)))
    sim_writer = sim.write_vcd('test_gpio.vcd')
    with sim_writer:
        sim.run()


if __name__ == '__main__':
    test_gpio()

