"""Simple GPIO peripheral on wishbone

This is an extremely simple GPIO peripheral intended for use in XICS
testing, however it could also be used as an actual GPIO peripheral

Modified for use with pinmux, will probably change the class name later.
"""
from random import randint
from math import ceil, floor
from nmigen import Elaboratable, Module, Signal, Record, Array, Cat, Const
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
        self.wordsize = wordsize
        self.n_gpio = n_gpio
        self.n_rows = ceil(self.n_gpio / self.wordsize)
        print("SimpleGPIO: WB Data # of bytes: {0}, #GPIOs: {1}, Rows: {2}"
              .format(self.wordsize, self.n_gpio, self.n_rows))
        class Spec: pass
        spec = Spec()
        spec.addr_wid = 30
        spec.mask_wid = 4
        spec.reg_wid = wordsize*8 # 32
        self.bus = Record(make_wb_layout(spec), name="gpio_wb")

        temp = []
        for i in range(self.n_gpio):
            name = "gpio{}".format(i)
            temp.append(Record(name=name, layout=gpio_layout))
        self.gpio_ports = Array(temp)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync

        bus = self.bus
        wb_rd_data = bus.dat_r
        wb_wr_data = bus.dat_w
        wb_ack = bus.ack

        gpio_ports = self.gpio_ports

        # MultiCSR read and write buses
        rd_multi = []
        for i in range(self.wordsize):
            name = "rd_word%d" % i
            rd_multi.append(Record(name=name, layout=csrbus_layout))

        wr_multi = []
        for i in range(self.wordsize):
            name = "wr_word%d" % i
            wr_multi.append(Record(name=name, layout=csrbus_layout))

        # Connecting intermediate signals to the WB data buses
        # allows the use of Records/Layouts
        # Split the WB data into bytes for use with individual GPIOs
        comb += Cat(*wr_multi).eq(wb_wr_data)
        # Connect GPIO config bytes to form a single word
        comb += wb_rd_data.eq(Cat(*rd_multi))
        for i in range(len(bus.sel)):
            sync += rd_multi[i].eq(0)

        # One address used to configure CSR, set output, read input
        with m.If(bus.cyc & bus.stb):
            with m.If(bus.we): # write
                # Update the GPIO configs with sent parameters
                for i in range(len(bus.sel)):
                    GPIO_num = Signal(16) # fixed for now
                    comb += GPIO_num.eq(bus.adr*len(bus.sel)+i)
                    with m.If(bus.sel[i]):
                        sync += gpio_ports[GPIO_num].oe.eq(wr_multi[i].oe)
                        sync += gpio_ports[GPIO_num].puen.eq(wr_multi[i].puen)
                        sync += gpio_ports[GPIO_num].pden.eq(wr_multi[i].pden)
                        with m.If (wr_multi[i].oe):
                            sync += gpio_ports[GPIO_num].o.eq(wr_multi[i].io)
                        with m.Else():
                            sync += gpio_ports[GPIO_num].o.eq(0)
                        sync += gpio_ports[GPIO_num].bank.eq(wr_multi[i].bank)
            with m.Else(): # read
                # Update the read multi bus with current GPIO configs
                # not ack'ing as we need to wait 1 clk cycle before data ready
                for i in range(len(bus.sel)):
                    GPIO_num = Signal(16) # fixed for now
                    comb += GPIO_num.eq(bus.adr*len(bus.sel)+i)
                    with m.If(bus.sel[i]):
                        sync += rd_multi[i].oe.eq(gpio_ports[GPIO_num].oe)
                        sync += rd_multi[i].ie.eq(~gpio_ports[GPIO_num].oe)
                        sync += rd_multi[i].puen.eq(gpio_ports[GPIO_num].puen)
                        sync += rd_multi[i].pden.eq(gpio_ports[GPIO_num].pden)
                        with m.If (gpio_ports[GPIO_num].oe):
                            sync += rd_multi[i].io.eq(gpio_ports[GPIO_num].o)
                        with m.Else():
                            sync += rd_multi[i].io.eq(gpio_ports[GPIO_num].i)
                        sync += rd_multi[i].bank.eq(gpio_ports[GPIO_num].bank)
            sync += wb_ack.eq(1) # ack after latching data
        with m.Else():
            sync += wb_ack.eq(0)

        return m

    def __iter__(self):
        for field in self.bus.fields.values():
            yield field
        for gpio in range(len(self.gpio_ports)):
            for field in self.gpio_ports[gpio].fields.values():
                yield field

    def ports(self):
        return list(self)

"""
def gpio_test_in_pattern(dut, pattern):
    num_gpios = len(dut.gpio_ports)
    print("Test pattern:")
    print(pattern)
    for pat in range(0, len(pattern)):
        for gpio in range(0, num_gpios):
            yield gpio_set_in_pad(dut, gpio, pattern[pat])
            yield
            temp = yield from gpio_rd_input(dut, gpio)
            print("Pattern: {0}, Reading {1}".format(pattern[pat], temp))
            assert (temp == pattern[pat])
            pat += 1
            if pat == len(pattern):
                break
"""

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
    def __init__(self, shift_dict):
        self.shift_dict = shift_dict
        self.oe=0
        self.ie=1 # By default gpio set as input
        self.puen=0
        self.pden=0
        self.io=0
        self.bank=0
        self.packed=0

    def set(self, oe=0, ie=0, puen=0, pden=0, io=0, bank=0):
        self.oe=oe
        self.ie=ie
        self.puen=puen
        self.pden=pden
        self.io=io
        self.bank=bank
        self.pack() # Produce packed byte for sending

    def set_out(self, outval):
        self.io=outval
        self.pack() # Produce packed byte for sending

    # Take config parameters of specified GPIOs, and combine them to produce
    # bytes for sending via WB bus
    def pack(self):
        self.packed = ((self.oe   << self.shift_dict['oe'])
                     | (self.ie   << self.shift_dict['ie'])
                     | (self.puen << self.shift_dict['puen'])
                     | (self.pden << self.shift_dict['pden'])
                     | (self.io   << self.shift_dict['io'])
                     | (self.bank << self.shift_dict['bank']))

        #print("GPIO Packed CSR: {0:x}".format(self.packed))

# Object for storing each gpio's config state

class GPIOManager():
    def __init__(self, dut, layout, wb_bus):
        self.dut = dut
        self.wb_bus = wb_bus
        # arrangement of config bits making up csr word
        self.csr_layout = layout
        self.shift_dict = self._create_shift_dict()
        self.n_gpios = len(self.dut.gpio_ports)
        print(dir(self.dut))
        # Get the number of bits of the WB sel signal
        # indicates the number of gpios per address
        self.n_gp_per_adr = len(self.dut.bus.sel)
        # Shows if data is byte/half-word/word/qword addressable?
        self.granuality = len(self.dut.bus.dat_w) // self.n_gp_per_adr
        self.n_rows = ceil(self.n_gpios / self.n_gp_per_adr)
        self.shadow_csr = []
        for i in range(self.n_gpios):
            self.shadow_csr.append(GPIOConfigReg(self.shift_dict))

    def print_info(self):
        print("----------")
        print("GPIO Block Info:")
        print("Number of GPIOs: %d" % self.n_gpios)
        print("GPIOs per WB data word: %d" % self.n_gp_per_adr)
        print("WB data granuality: %d" % self.granuality)
        print("Number of address rows: %d" % self.n_rows)
        print("----------")

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
        print("Parsed GPIOs {0} until {1}".format(start, end))
        return start, end

    # Take a combined word and update shadow reg's
    # TODO: convert hard-coded sizes to use the csrbus_layout (or dict?)
    def update_single_shadow(self, csr_byte, gpio):
        oe   = (csr_byte >> self.shift_dict['oe']) & 0x1
        ie   = (csr_byte >> self.shift_dict['ie']) & 0x1
        puen = (csr_byte >> self.shift_dict['puen']) & 0x1
        pden = (csr_byte >> self.shift_dict['pden']) & 0x1
        io   = (csr_byte >> self.shift_dict['io']) & 0x1
        bank = (csr_byte >> self.shift_dict['bank']) & 0x3

        print("csr={0:x} | oe={1}, ie={2}, puen={3}, pden={4}, io={5}, bank={6}"
              .format(csr_byte, oe, ie, puen, pden, io, bank))

        self.shadow_csr[gpio].set(oe, ie, puen, pden, io, bank)
        return oe, ie, puen, pden, io, bank

    # Update multiple configuration registers
    def wr(self, gp_start, gp_end, check=False):
        # Some maths to determine how many transactions, and at which
        # address to start transmitting
        n_gp_config = gp_end - gp_start
        adr_start = gp_start // self.n_gp_per_adr
        n_adr = ceil(n_gp_config / self.n_gp_per_adr)

        curr_gpio = gp_start
        # cycle through addresses, each iteration is a WB tx
        for adr in range(adr_start, adr_start + n_adr):
            tx_sel = 0
            tx_word = 0
            # cycle through every WB sel bit, and add configs of
            # corresponding gpios
            for i in range(0, self.n_gp_per_adr):
                # if current gpio's location in the WB data word matches sel bit
                if (curr_gpio % self.n_gp_per_adr) == i:
                    print("gpio%d" % curr_gpio)
                    tx_sel += 1 << i
                    tx_word += (self.shadow_csr[curr_gpio].packed
                                << (self.granuality * i))
                    curr_gpio += 1
                    # stop if we processed all required gpios
                    if curr_gpio >= gp_end:
                        break
            print("Adr: %x | Sel: %x | TX Word: %x" % (adr, tx_sel, tx_word))
            yield from wb_write(self.wb_bus, adr, tx_word, tx_sel)
            yield # Allow one clk cycle to propagate

            if(check):
                row_word = yield from wb_read(self.wb_bus, adr, tx_sel)
                assert config_word == read_word

    def rd(self, gp_start, gp_end):
        # Some maths to determine how many transactions, and at which
        # address to start transmitting
        n_gp_config = gp_end - gp_start
        adr_start = gp_start // self.n_gp_per_adr
        n_adr = ceil(n_gp_config / self.n_gp_per_adr)

        curr_gpio = gp_start
        # cycle through addresses, each iteration is a WB tx
        for adr in range(adr_start, adr_start + n_adr):
            tx_sel = 0
            # cycle through every WB sel bit, and add configs of
            # corresponding gpios
            for i in range(0, self.n_gp_per_adr):
                # if current gpio's location in the WB data word matches sel bit
                if (curr_gpio % self.n_gp_per_adr) == i:
                    print("gpio%d" % curr_gpio)
                    tx_sel += 1 << i
                    curr_gpio += 1
                    # stop if we processed all required gpios
                    if curr_gpio >= gp_end:
                        break
            print("Adr: %x | Sel: %x " % (adr, tx_sel))
            row_word = yield from wb_read(self.wb_bus, adr, tx_sel)

            mask = (2**self.granuality) - 1
            for i in range(self.n_gp_per_adr):
                if ((tx_sel >> i) & 1) == 1:
                    single_csr = (row_word >> (i*self.granuality)) & mask
                    curr_gpio = adr*self.n_gp_per_adr + i
                    #print("rd gpio%d" % curr_gpio)
                    self.update_single_shadow(single_csr, curr_gpio)

    # Write all shadow registers to GPIO block
    def wr_all(self, check=False):
        for row in range(0, self.n_rows):
            yield from self.wr(0, self.n_gpios, check)

    # Read all GPIO block row addresses and update shadow reg's
    def rd_all(self, check=False):
        for row in range(0, self.n_rows):
            yield from self.rd(0, self.n_gpios)

    def config(self, gpio_str, oe, ie, puen, pden, outval, bank, check=False):
        start, end = self._parse_gpio_arg(gpio_str)
        # Update the shadow configuration
        for gpio in range(start, end):
            # print(oe, ie, puen, pden, outval, bank)
            self.shadow_csr[gpio].set(oe, ie, puen, pden, outval, bank)
        # TODO: only update the required rows?
        #yield from self.wr_all()
        yield from self.wr(start, end)

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

        yield from self.wr(start, end)

    def rd_input(self, gpio_str):
        start, end = self._parse_gpio_arg(gpio_str)
        #read_data = [0] * self.n_rows
        #for row in range(0, self.n_rows):
        #    read_data[row] = yield from self.rd_row(row)
        yield from self.rd(start, end)

        num_to_read = (end - start)
        read_in = [0] * num_to_read
        curr_gpio = 0
        for i in range(0, num_to_read):
            read_in[i] = self.shadow_csr[curr_gpio].io
            curr_gpio += 1

        print("GPIOs %d until %d, i=%s".format(start, end, read_in))
        return read_in

    # TODO: There's probably a cleaner way to clear the bit...
    def sim_set_in_pad(self, gpio_str, in_val):
        start, end = self._parse_gpio_arg(gpio_str)
        for gpio in range(start, end):
            old_in_val = yield self.dut.gpio_ports[gpio].i
            print(old_in_val)
            print("GPIO{0} Previous i: {1:b} | New i: {2:b}"
                  .format(gpio, old_in_val, in_val))
            yield self.dut.gpio_ports[gpio].i.eq(in_val)
            yield # Allow one clk cycle to propagate

    def rd_shadow(self):
        shadow_csr = [0] * self.n_gpios
        for gpio in range(0, self.n_gpios):
            shadow_csr[gpio] = self.shadow_csr[gpio].packed

        hex_str = ""
        for reg in shadow_csr:
            hex_str += " "+hex(reg)
        print("Shadow reg's: ", hex_str)

        return shadow_csr


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

def gen_gtkw_doc(n_gpios, wordsize, filename):
    # GTKWave doc generation
    wb_data_width = wordsize*8
    n_rows = ceil(n_gpios/wordsize)
    style = {
        '': {'base': 'hex'},
        'in': {'color': 'orange'},
        'out': {'color': 'yellow'},
        'debug': {'module': 'top', 'color': 'red'}
    }

    # Create a trace list, each block expected to be a tuple()
    traces = []
    wb_traces = ('Wishbone Bus', [
                        ('gpio_wb__cyc', 'in'),
                        ('gpio_wb__stb', 'in'),
                        ('gpio_wb__we', 'in'),
                        ('gpio_wb__adr[27:0]', 'in'),
                        ('gpio_wb__sel[3:0]', 'in'),
                        ('gpio_wb__dat_w[{}:0]'.format(wb_data_width-1), 'in'),
                        ('gpio_wb__dat_r[{}:0]'.format(wb_data_width-1), 'out'),
                        ('gpio_wb__ack', 'out'),
                ])
    traces.append(wb_traces)

    gpio_internal_traces = ('Internal', [
                                ('clk', 'in'),
                                ('new_transaction'),
                                ('rst', 'in')
                            ])
    traces.append(gpio_internal_traces)

    traces.append({'comment': 'Multi-byte GPIO config read bus'})
    for word in range(0, wordsize):
        prefix = "rd_word{}__".format(word)
        single_word = []
        word_signals = []
        single_word.append('Word{}'.format(word))
        word_signals.append((prefix+'bank[{}:0]'.format(NUMBANKBITS-1)))
        word_signals.append((prefix+'ie'))
        word_signals.append((prefix+'io'))
        word_signals.append((prefix+'oe'))
        word_signals.append((prefix+'pden'))
        word_signals.append((prefix+'puen'))
        single_word.append(word_signals)
        traces.append(tuple(single_word))

    traces.append({'comment': 'Multi-byte GPIO config write bus'})
    for word in range(0, wordsize):
        prefix = "wr_word{}__".format(word)
        single_word = []
        word_signals = []
        single_word.append('Word{}'.format(word))
        word_signals.append((prefix+'bank[{}:0]'.format(NUMBANKBITS-1)))
        word_signals.append((prefix+'ie'))
        word_signals.append((prefix+'io'))
        word_signals.append((prefix+'oe'))
        word_signals.append((prefix+'pden'))
        word_signals.append((prefix+'puen'))
        single_word.append(word_signals)
        traces.append(tuple(single_word))

    for gpio in range(0, n_gpios):
        prefix = "gpio{}__".format(gpio)
        single_gpio = []
        gpio_signals = []
        single_gpio.append('GPIO{} Port'.format(gpio))
        gpio_signals.append((prefix+'bank[{}:0]'.format(NUMBANKBITS-1), 'out'))
        gpio_signals.append( (prefix+'i', 'in') )
        gpio_signals.append( (prefix+'o', 'out') )
        gpio_signals.append( (prefix+'oe', 'out') )
        gpio_signals.append( (prefix+'pden', 'out') )
        gpio_signals.append( (prefix+'puen', 'out') )
        single_gpio.append(gpio_signals)
        traces.append(tuple(single_gpio))

    #print(traces)

    #module = "top.xics_icp"
    module = "bench.top.xics_icp"
    write_gtkw(filename+".gtkw", filename+".vcd", traces, style,
               module=module)

def test_gpio():
    filename = "test_gpio" # Doesn't include extension
    n_gpios = 8
    wordsize = 4 # Number of bytes in the WB data word
    dut = SimpleGPIO(wordsize, n_gpios)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open(filename+".il", "w") as f:
        f.write(vl)

    m = Module()
    m.submodules.xics_icp = dut

    sim = Simulator(m)
    sim.add_clock(1e-6)

    #sim.add_sync_process(wrap(sim_gpio(dut, use_random=False)))
    sim.add_sync_process(wrap(test_gpioman(dut)))
    sim_writer = sim.write_vcd(filename+".vcd")
    with sim_writer:
        sim.run()

    gen_gtkw_doc(n_gpios, wordsize, filename)

def test_gpioman(dut):
    print("------START----------------------")
    gpios = GPIOManager(dut, csrbus_layout, dut.bus)
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
    yield from gpios.config("0-1", oe=1, ie=0, puen=0, pden=1, outval=0, bank=2)
    ie = 1
    yield from gpios.config("5-7", oe=0, ie=1, puen=0, pden=1, outval=0, bank=6)
    yield from gpios.set_out("0-1", outval=1)

    #yield from gpios.rd_all()
    yield from gpios.sim_set_in_pad("6-7", 1)
    print("----------------------------")
    yield from gpios.rd_input("4-7")

    gpios.rd_shadow()

if __name__ == '__main__':
    test_gpio()

