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

cxxsim = False
if cxxsim:
    from nmigen.sim.cxxsim import Simulator, Settle
else:
    from nmigen.sim import Simulator, Settle

# Layout of 8-bit configuration word:
# bank[2:0] i/o | pden puen ien oe
NUMBANKBITS = 3 # max 3 bits, only supporting 4 banks (0-3)
csrbus_layout = (("oe", 1),
                 ("ie", 1),
                 ("puen", 1),
                 ("pden", 1),
                 ("io", 1),
                 ("bank", NUMBANKBITS)
                )

gpio_layout = (("i", 1),
               ("oe", 1),
               ("o", 1),
               ("puen", 1),
               ("pden", 1),
               ("bank", NUMBANKBITS)
              )

class SimpleGPIO(Elaboratable):

    def __init__(self, wordsize=4, n_gpio=16):
        print("WB Data # of bytes: {0}, # of GPIOs: {1}"
                .format(wordsize, n_gpio))
        self.wordsize = wordsize
        self.n_gpio = n_gpio
        class Spec: pass
        spec = Spec()
        spec.addr_wid = 30
        spec.mask_wid = 4
        spec.reg_wid = wordsize*8 # 32
        self.bus = Record(make_wb_layout(spec), name="gpio_wb")

        print("CSRBUS layout: ", csrbus_layout)
        # create array - probably a cleaner way to do this...
        temp = []
        for i in range(0, self.wordsize):
            temp_str = "word{}".format(i)
            temp.append(Record(name=temp_str, layout=csrbus_layout))
        self.multicsrbus = Array(temp)

        temp = []
        for i in range(0, n_gpio):
            temp_str = "gpio{}".format(i)
            temp.append(Record(name=temp_str, layout=gpio_layout))
        self.gpio_ports = Array(temp)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync

        bus = self.bus
        wb_rd_data = bus.dat_r
        wb_wr_data = bus.dat_w
        wb_ack = bus.ack

        gpio_ports = self.gpio_ports
        # csrbus = self.csrbus
        multi = self.multicsrbus

        comb += wb_ack.eq(0)

        gpio_addr = Signal(log2_int(self.n_gpio))
        # Flag for indicating rd/wr transactions
        new_transaction = Signal(1)

        #print("Types:")
        #print("gpio_addr: ", type(gpio_addr))

        # One address used to configure CSR, set output, read input
        with m.If(bus.cyc & bus.stb):
            comb += wb_ack.eq(1) # always ack
            sync += gpio_addr.eq(bus.adr)
            sync += new_transaction.eq(1)
            with m.If(bus.we): # write
                # Configure CSR
                for byte in range(0, self.wordsize):
                    sync += multi[byte].eq(wb_wr_data[byte*8:8+byte*8])
            with m.Else(): # read
                # Concatinate the GPIO configs that are on the same "row" or
                # address and send
                multi_cat = []
                for i in range(0, self.wordsize):
                    multi_cat.append(multi[i])
                comb += wb_rd_data.eq(Cat(multi_cat))
        with m.Else():
            sync += new_transaction.eq(0)
            # Update the state of "io" while no WB transactions
            for byte in range(0, self.wordsize):
                with m.If(gpio_ports[gpio_addr+byte].oe):
                    sync += multi[byte].io.eq(gpio_ports[gpio_addr+byte].o)
                with m.Else():
                    sync += multi[byte].io.eq(gpio_ports[gpio_addr+byte].i)
        # Only update GPIOs config if a new transaction happened last cycle
        # (read or write). Always lags from csrbus by 1 clk cycle, most
        # sane way I could think of while using Record().
        with m.If(new_transaction):
            for byte in range(0, self.wordsize):
                sync += gpio_ports[gpio_addr+byte].oe.eq(multi[byte].oe)
                sync += gpio_ports[gpio_addr+byte].puen.eq(multi[byte].puen)
                sync += gpio_ports[gpio_addr+byte].pden.eq(multi[byte].pden)
                # Check to prevent output being set if GPIO configured as input
                # NOTE: No checking is done if ie/oe high together
                with m.If(gpio_ports[gpio_addr+byte].oe):
                    sync += gpio_ports[gpio_addr+byte].o.eq(multi[byte].io)
                sync += gpio_ports[gpio_addr+byte].bank.eq(multi[byte].bank)
        return m

    def __iter__(self):
        for field in self.bus.fields.values():
            yield field
        #yield self.gpio_o

    def ports(self):
        return list(self)

# The shifting of control bits in the configuration word is dependent on the
# defined layout. To prevent maintaining the shift constants in a separate
# location, the same layout is used to generate a dictionary of bit shifts
# with which the configuration word can be produced!
def create_shift_dict():
    shift = 0
    shift_dict = {}
    for i in range(0, len(csrbus_layout)):
        shift_dict[csrbus_layout[i][0]] = shift
        shift += csrbus_layout[i][1]
    print(shift_dict)
    return shift_dict

def config_to_csr(oe, ie, puen, pden, outval, bank):
    shift_dict = create_shift_dict()
    csr_val = ( (oe   << shift_dict['oe'])
              | (ie   << shift_dict['ie'])
              | (puen << shift_dict['puen'])
              | (pden << shift_dict['pden'])
              | (outval << shift_dict['io'])
              | (bank << shift_dict['bank']) )

    print("Created CSR value: {0:x}".format(csr_val))

    return csr_val # return the config state


# TODO: probably make into class (or return state in a variable) 
def gpio_config(dut, gpio, oe, ie, puen, pden, outval, bank, gpio_end=-1, check=False, wordsize=4):
    csr_val = config_to_csr(oe, ie, puen, pden, outval, bank)
    if gpio_end == -1:
        # Single gpio configure
        print("Configuring GPIO{0} CSR to {1:x}".format(gpio, csr_val))
        yield from wb_write(dut.bus, gpio, csr_val)
        yield # Allow one clk cycle to propagate
    else:
        if gpio > gpio_end:
            print("ERROR! Last GPIO given {0} is lower than the start GPIO {1}"
                  .format(gpio_end, gpio))
            #exit()
        else:
            single_csr = csr_val
            n_gpios = gpio_end - gpio + 1
            n_rows = ceil(n_gpios / wordsize)
            print("Num of GPIOs: {0}, Num of rows: {1}".format(n_gpios, n_rows))
            curr_gpio = gpio
            start_addr = floor(gpio / wordsize)
            for row in range(0, n_rows):
                temp = 0
                start_byte = curr_gpio % wordsize
                for byte in range(start_byte, wordsize):
                    if curr_gpio > n_gpios:
                        break
                    temp += single_csr << (8 * byte)
                    curr_gpio += 1
                print("Configuring CSR to {0:x} to addr: {1:x}"
                        .format(temp, start_addr+row))
                yield from wb_write(dut.bus, start_addr+row, temp)
                yield # Allow one clk cycle to propagate 
    if(check):
        # Check the written value
        test_csr = yield from gpio_rd_csr(dut, gpio)
        assert test_csr == csr_val

    return csr_val # return the config state

# Not used normally - only for debug
def reg_write(dut, gpio, reg_val):
    print("Configuring CSR to {0:x}".format(reg_val))
    yield from wb_write(dut.bus, gpio, reg_val)

# TODO: Return the configuration states
def gpio_rd_csr(dut, gpio):
    shift_dict = create_shift_dict()
    csr_val = yield from wb_read(dut.bus, gpio)
    print("GPIO{0} | CSR: {1:x}".format(gpio, csr_val))
    print("Output Enable: {0:b}".format((csr_val >> shift_dict['oe']) & 1))
    print("Input Enable: {0:b}".format((csr_val >> shift_dict['ie']) & 1))
    print("Pull-Up Enable: {0:b}".format((csr_val >> shift_dict['puen']) & 1))
    print("Pull-Down Enable: {0:b}".format((csr_val >> shift_dict['pden']) & 1))
    if ((csr_val >> shift_dict['oe']) & 1):
        print("Output: {0:b}".format((csr_val >> shift_dict['io']) & 1))
    else:
        print("Input: {0:b}".format((csr_val >> shift_dict['io']) & 1))
    bank_mask = (2**NUMBANKBITS)-1
    print("Bank: {0:b}".format((csr_val >> shift_dict['bank']) & bank_mask))
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
    num_gpios = len(dut.gpio_ports)
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

def test_gpio_single(dut, gpio, use_random=True):
    oe = 1
    ie = 0
    output = 0
    puen = 0
    pden = 0
    if use_random:
        bank = randint(0, (2**NUMBANKBITS)-1)
        print("Random bank select: {0:b}".format(bank))
    else:
        bank = 3 # not special, chose for testing

    gpio_csr = yield from gpio_config(dut, gpio, oe, ie, puen, pden, output,
                                      bank, check=True)
    # Enable output
    output = 1
    gpio_csr = yield from gpio_config(dut, gpio, oe, ie, puen, pden, output,
                                      bank, check=True) 


def sim_gpio(dut, use_random=True):
    num_gpios = len(dut.gpio_ports)
    #print(dut)
    #print(dir(dut.gpio_ports))
    #print(len(dut.gpio_ports))
    #if use_random:
    #    bank = randint(0, (2**NUMBANKBITS)-1)
    #    print("Random bank select: {0:b}".format(bank))
    #else:
    #    bank = 3 # not special, chose for testing
    """
    oe = 1
    ie = 0
    output = 0
    puen = 0 # 1
    pden = 0
    gpio_csr = [0] * num_gpios
    # Configure GPIOs for 
    for gpio in range(0, num_gpios):
        gpio_csr[gpio] = yield from gpio_config(dut, gpio, oe, ie, puen, 
                                                   pden, output, bank)
    # Set outputs
    output = 1
    for gpio in range(0, num_gpios):
        yield from gpio_set_out(dut, gpio, gpio_csr[gpio], output)

    # Read CSR
    for gpio in range(0, num_gpios):
        temp_csr = yield from gpio_rd_csr(dut, gpio)
        assert ((temp_csr>>IOSHIFT) & 1) == output
    # Configure for input
    oe = 0
    ie = 1
    for gpio in range(0, num_gpios):
        gpio_csr[gpio] = yield from gpio_config(dut, gpio, oe, ie, puen,
                                                   pden, output, bank)

        temp = yield from gpio_rd_input(dut, gpio)
        assert temp == 0

        yield from gpio_set_in_pad(dut, gpio, 1)
        temp = yield from gpio_rd_input(dut, gpio)
        assert temp == 1

    # TODO: not working yet
    #test_pattern = []
    #for i in range(0, (num_gpios * 2)):
    #    test_pattern.append(randint(0,1))
    #yield from gpio_test_in_pattern(dut, test_pattern)
    """

    #yield from test_gpio_single(dut, 0, use_random)
    #yield from test_gpio_single(dut, 1, use_random)
    oe = 1
    ie = 0
    puen = 0
    pden = 1
    outval = 1
    bank = 2
    start_gpio = 1
    end_gpio = 6
    yield from gpio_config(dut, start_gpio, oe, ie, puen, pden, outval, bank, end_gpio, check=False, wordsize=4)
    #reg_val = 0xC56271A2
    #reg_val =  0xFFFFFFFF
    #yield from reg_write(dut, 0, reg_val)
    #yield from reg_write(dut, 0, reg_val)
    #yield

    #csr_val = yield from wb_read(dut.bus, 0)
    #print("CSR Val: {0:x}".format(csr_val))
    print("Finished the simple GPIO block test!")

def test_gpio():
    num_gpio = 8
    wordsize = 4 # Number of bytes in the WB data word
    dut = SimpleGPIO(wordsize, num_gpio)
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

