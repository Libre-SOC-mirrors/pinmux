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
        print("SimpleGPIO: WB Data # of bytes: {0}, # of GPIOs: {1}"
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
        for i in range(self.wordsize):
            temp_str = "word{}".format(i)
            temp.append(Record(name=temp_str, layout=csrbus_layout))
        self.multicsrbus = Array(temp)

        temp = []
        for i in range(self.n_gpio):
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
        multi = self.multicsrbus

        comb += wb_ack.eq(0)

        row_start = Signal(log2_int(self.n_gpio))
        # Flag for indicating rd/wr transactions
        new_transaction = Signal(1)

        #print("Types:")
        #print("gpio_addr: ", type(gpio_addr))

        # One address used to configure CSR, set output, read input
        with m.If(bus.cyc & bus.stb):
            comb += wb_ack.eq(1) # always ack
            # Probably wasteful
            sync += row_start.eq(bus.adr * self.wordsize)
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
                with m.If(gpio_ports[row_start+byte].oe):
                    sync += multi[byte].io.eq(gpio_ports[row_start+byte].o)
                with m.Else():
                    sync += multi[byte].io.eq(gpio_ports[row_start+byte].i)
        # Only update GPIOs config if a new transaction happened last cycle
        # (read or write). Always lags from multi csrbus by 1 clk cycle, most
        # sane way I could think of while using Record().
        with m.If(new_transaction):
            for byte in range(0, self.wordsize):
                sync += gpio_ports[row_start+byte].oe.eq(multi[byte].oe)
                sync += gpio_ports[row_start+byte].puen.eq(multi[byte].puen)
                sync += gpio_ports[row_start+byte].pden.eq(multi[byte].pden)
                # Check to prevent output being set if GPIO configured as input
                # TODO: No checking is done if ie/oe high together
                with m.If(gpio_ports[row_start+byte].oe):
                    sync += gpio_ports[row_start+byte].o.eq(multi[byte].io)
                sync += gpio_ports[row_start+byte].bank.eq(multi[byte].bank)
        return m

    def __iter__(self):
        for field in self.bus.fields.values():
            yield field
        #yield self.gpio_o

    def ports(self):
        return list(self)

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

# Shadow reg container class
class GPIOConfigReg():
    def __init__(self):
        self.oe=0
        self.ie=0
        self.puen=0
        self.pden=0
        self.io=0
        self.bank=0

    def set(self, oe=0, ie=0, puen=0, pden=0, outval=0, bank=0):
        self.oe=oe
        self.ie=ie
        self.puen=puen
        self.pden=pden
        self.io=outval
        self.bank=bank

    def set_out(self, outval):
        self.io=outval

# Object for storing each gpio's config state

class GPIOManager():
    def __init__(self, dut, layout):
        self.dut = dut
        # arrangement of config bits making up csr word
        self.csr_layout = layout
        self.shift_dict = self._create_shift_dict()
        self.n_gpios = len(self.dut.gpio_ports)
        print(dir(self.dut))
        # Since GPIO HDL block already has wordsize parameter, use directly
        # Alternatively, can derive from WB data r/w buses (div by 8 for bytes)
        #self.wordsize = len(self.dut.gpio_wb__dat_w) / 8
        self.wordsize = self.dut.wordsize
        self.n_rows = ceil(self.n_gpios / self.wordsize)
        self.shadow_csr = []
        for i in range(self.n_gpios):
            self.shadow_csr.append(GPIOConfigReg())

    # The shifting of control bits in the configuration word is dependent on the
    # defined layout. To prevent maintaining the shift constants in a separate
    # location, the same layout is used to generate a dictionary of bit shifts
    # with which the configuration word can be produced!
    def _create_shift_dict(self):
        shift = 0
        shift_dict = {}
        for i in range(0, len(self.csr_layout)):
            shift_dict[self.csr_layout[i][0]] = shift
            shift += self.csr_layout[i][1]
        print(shift_dict)
        return shift_dict

    def _parse_gpio_arg(self, gpio_str):
        # TODO: No input checking!
        print("Given GPIO/range string: {}".format(gpio_str))
        if gpio_str == "all":
            start = 0
            end = self.n_gpios
        elif '-' in gpio_str:
            start, end = gpio_str.split('-')
            start = int(start)
            end = int(end) + 1
            if (end < start) or (end > self.n_gpios):
                raise Exception("Second GPIO must be higher than first and"
                        + " must be lower or equal to last available GPIO.")
        else:
            start = int(gpio_str)
            if start >= self.n_gpios:
                raise Exception("GPIO must be less/equal to last GPIO.")
            end = start + 1
        print("Setting config for GPIOs {0} until {1}".format(start, end))
        return start, end

    # Take config parameters of specified GPIOs, and combine them to produce
    # bytes for sending via WB bus
    def _pack_csr(self, start, end):
        #start, end = self._parse_gpio_arg(gpio_str)
        num_csr = end-start
        csr = [0] * num_csr
        for i in range(0, num_csr):
            gpio = i + start
            print("Pack: gpio{}".format(gpio))
            csr[i] = ((self.shadow_csr[gpio].oe     << self.shift_dict['oe'])
                    | (self.shadow_csr[gpio].ie     << self.shift_dict['ie'])
                    | (self.shadow_csr[gpio].puen   << self.shift_dict['puen'])
                    | (self.shadow_csr[gpio].pden   << self.shift_dict['pden'])
                    | (self.shadow_csr[gpio].io << self.shift_dict['io'])
                    | (self.shadow_csr[gpio].bank   << self.shift_dict['bank']))

            print("GPIO{0} Packed CSR: {1:x}".format(gpio, csr[i]))

        return csr # return the config byte list

    def rd_csr(self, row_start):
        row_word = yield from wb_read(self.dut.bus, row_start)
        print("Returned CSR: {0:x}".format(row_word))
        return row_word

    def rd_input(self, row_start):
        in_val = yield from wb_read(dut.bus, gpio)
        in_val = (in_val >> IOSHIFT) & 1
        print("GPIO{0} | Input: {1:b}".format(gpio, in_val))
        return in_val

    def print_info(self):
        print("----------")
        print("GPIO Block Info:")
        print("Number of GPIOs: {}".format(self.n_gpios))
        print("WB Data bus width (in bytes): {}".format(self.wordsize))
        print("Number of rows: {}".format(self.n_rows))
        print("----------")

    # Write all shadow registers to GPIO block
    def wr_all(self):
        # UPDATE using ALL shadow registers
        csr = self._pack_csr(0, self.n_gpios)
        #start_addr = floor(start / self.wordsize)
        start_addr = 0
        curr_gpio = 0
        for row in range(0, self.n_rows):
            row_word = 0
            start_byte = curr_gpio % self.wordsize
            for byte in range(start_byte, self.wordsize):
                if curr_gpio > self.n_gpios:
                    break
                #row_word += csr[byte] << (8 * byte)
                row_word += csr[curr_gpio] << (8 * byte)
                curr_gpio += 1
            print("Configuring CSR to {0:x} to addr: {1:x}"
                    .format(row_word, start_addr+row))
            yield from wb_write(self.dut.bus, start_addr+row, row_word)
            yield # Allow one clk cycle to propagate

            if(True): #check):
                test_row = yield from self.rd_csr(start_addr+row)
                assert row_word == test_row


    def config(self, gpio_str, oe, ie, puen, pden, outval, bank, check=False):
        start, end = self._parse_gpio_arg(gpio_str)
        # Update the shadow configuration
        for gpio in range(start, end):
            print(oe, ie, puen, pden, outval, bank)
            self.shadow_csr[gpio].set(oe, ie, puen, pden, outval, bank)

        yield from self.wr_all()

    # Set/Clear the output bit for single or group of GPIOs
    def set_out(self, gpio_str, outval):
        start, end = self._parse_gpio_arg(gpio_str)
        for gpio in range(start, end):
            self.shadow_csr[gpio].set_out(outval)

        if start == end:
            print("Setting GPIO{0} output to {1}".format(start, outval))
        else:
            print("Setting GPIOs {0}-{1} output to {2}"
                  .format(start, end-1, outval))

        yield from self.wr_all()
    """
    # Not used normally - only for debug
    def reg_write(dut, gpio, reg_val):
        print("Configuring CSR to {0:x}".format(reg_val))
        yield from wb_write(dut.bus, gpio, reg_val)

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
    """

def sim_gpio(dut, use_random=True):
    #print(dut)
    #print(dir(dut.gpio_ports))
    #print(len(dut.gpio_ports))

    gpios = GPIOManager(dut, csrbus_layout)
    gpios.print_info()
    # TODO: not working yet
    #test_pattern = []
    #for i in range(0, (num_gpios * 2)):
    #    test_pattern.append(randint(0,1))
    #yield from gpio_test_in_pattern(dut, test_pattern)

    #yield from gpio_config(dut, start_gpio, oe, ie, puen, pden, outval, bank, end_gpio, check=False, wordsize=4)
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

    #sim.add_sync_process(wrap(sim_gpio(dut, use_random=False)))
    sim.add_sync_process(wrap(test_gpioman(dut)))
    sim_writer = sim.write_vcd('test_gpio.vcd')
    with sim_writer:
        sim.run()

def test_gpioman(dut):
    gpios = GPIOManager(dut, csrbus_layout)
    gpios.print_info()
    #gpios._parse_gpio_arg("all")
    #gpios._parse_gpio_arg("0")
    #gpios._parse_gpio_arg("1-3")
    #gpios._parse_gpio_arg("20")

    oe = 1
    ie = 0
    puen = 0
    pden = 1
    outval = 0
    bank = 3
    yield from gpios.config("0-3", oe=1, ie=0, puen=0, pden=1, outval=0, bank=2)
    ie = 1
    yield from gpios.config("4-7", oe=0, ie=1, puen=0, pden=1, outval=0, bank=2)
    yield from gpios.set_out("0-3", outval=1)


if __name__ == '__main__':
    test_gpio()

