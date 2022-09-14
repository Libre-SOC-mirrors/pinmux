#!/usr/bin/env python3
"""
pinmux documented here https://libre-soc.org/docs/pinmux/
"""
from nmigen import Elaboratable, Module, Signal, Record, Array, Cat
from nmigen.hdl.rec import Layout
from nmigen.utils import log2_int
from nmigen.cli import rtlil
from soc.minerva.wishbone import make_wb_layout
from nmutil.util import wrap
#from soc.bus.test.wb_rw import wb_read, wb_write

from nmutil.gtkw import write_gtkw

cxxsim = False
if cxxsim:
    from nmigen.sim.cxxsim import Simulator, Settle, Delay
else:
    from nmigen.sim import Simulator, Settle, Delay

from iomux import IOMuxBlockSingle

io_layout = (("i", 1),
             ("oe", 1),
             ("o", 1)
            )

uart_layout = (("rx", 1),
               ("tx", 1),
               ("oe", 1)
              )
uart_tx_layout = (("o", 1),
                 ("oe", 1)
                 )
GPIO_BANK = 0
UART_BANK = 1
I2C_BANK = 2

"""
Really basic example, uart tx/rx and i2c sda/scl pinmux
"""
class ManPinmux(Elaboratable):
    def __init__(self, requested):
        print("Test Manual Pinmux!")

        self.requested = requested
        self.n_banks = 4
        self.bank = Signal(log2_int(self.n_banks))
        self.pads = {}
        self.muxes = {}
        # Automatically create the necessary periph/pad Records/Signals
        # depending on the given dict specification
        for pad in self.requested.keys():
            self.pads[pad] = {}
            self.pads[pad]["pad"] = Record(name=pad, layout=io_layout)
            self.muxes[pad] = IOMuxBlockSingle(self.n_banks)
            for mux in self.requested[pad].keys():
                periph = self.requested[pad][mux][0]
                unit_num = self.requested[pad][mux][1]
                if len(self.requested[pad][mux]) == 3:
                    pin = self.requested[pad][mux][2]
                else:
                    pin = "io"
                if periph == "gpio":
                    self.pads[pad][mux] = Record(name="gp%d" % unit_num,
                                                 layout=io_layout)
                elif periph == "uart":
                    if pin == "tx":
                        self.pads[pad][mux] = Record(name="tx%d" % unit_num,
                                                     layout=uart_tx_layout)
                    elif pin == "rx":
                        self.pads[pad][mux] = Signal(name="rx%d" % unit_num)
                elif periph == "i2c":
                    if pin == "sda":
                        self.pads[pad][mux] = Record(name="sda%d" % unit_num,
                                                     layout=io_layout)
                    elif pin == "scl":
                        self.pads[pad][mux] = Record(name="scl%d" % unit_num,
                                                     layout=io_layout)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync
        muxes = self.muxes
        bank = self.bank
        pads = self.pads
        for pad in pads.keys():
            m.submodules[pad+"_mux"] = muxes[pad]
            # all muxes controlled by the same multi-bit signal
            comb += muxes[pad].bank.eq(bank)

        # print(self.requested)
        # print(self.pads)

        # ---------------------------
        # This section connects the periphs to the assigned banks
        # ---------------------------
        for pad in pads.keys():
            for mux in self.requested[pad].keys():
                periph = self.requested[pad][mux][0]
                num = int(mux[3])
                if len(self.requested[pad][mux]) == 3:
                    pin = self.requested[pad][mux][2]
                else:
                    pin = "io"
                if periph == "gpio" or periph == "i2c":
                    comb += muxes[pad].bank_ports[num].o.eq(pads[pad][mux].o)
                    comb += muxes[pad].bank_ports[num].oe.eq(pads[pad][mux].oe)
                    comb += pads[pad][mux].i.eq(muxes[pad].bank_ports[num].i)
                elif periph == "uart":
                    if pin == "tx":
                        comb += muxes[pad].bank_ports[num].o.eq(
                                                           pads[pad][mux].o)
                        comb += muxes[pad].bank_ports[num].oe.eq(
                                                           pads[pad][mux].oe)
                    elif pin == "rx":
                        comb += pads[pad][mux].eq(muxes[pad].bank_ports[num].i)

        # ---------------------------
        # Here is where the muxes are assigned to the actual pads
        # ---------------------------
        for pad in pads.keys():
            comb += pads[pad]["pad"].o.eq(muxes[pad].out_port.o)
            comb += pads[pad]["pad"].oe.eq(muxes[pad].out_port.oe)
            comb += muxes[pad].out_port.i.eq(pads[pad]["pad"].i)

        return m

    def __iter__(self):
        for pad in list(self.pads.keys()):
            for field in self.pads[pad]["pad"].fields.values():
                yield field
            for mux in self.pads[pad].keys():
                if type(self.pads[pad][mux]) == Signal:
                    yield self.pads[pad][mux]
                else:
                    for field in self.pads[pad][mux].fields.values():
                        yield field
        yield self.bank

    def ports(self):
        return list(self)

def set_bank(dut, bank, delay=1e-6):
    yield dut.bank.eq(bank)
    yield Delay(delay)

"""
GPIO test function
Set the gpio output based on given data sequence, checked at pad.o
Then sends the same byte via pad.i to gpio input
"""
def gpio(gpio, pad, data, delay=1e-6):
    # Output test - Control GPIO output
    yield gpio.oe.eq(1)
    yield Delay(delay)
    n_bits = len(bin(data)[2:])
    read = 0
    for i in range(0, n_bits):
        bit = (data >> i) & 0x1
        yield gpio.o.eq(bit)
        yield Delay(delay)
        temp = yield pad.o
        read |= (temp << i)
    assert data == read, f"GPIO Sent: %x | Pad Read: %x" % (data, read)
    # Input test - Control Pad input
    yield gpio.oe.eq(0)
    yield Delay(delay)
    read2 = 0
    for i in range(0, n_bits):
        bit = (read >> i) & 0x1
        yield pad.i.eq(bit)
        yield Delay(delay)
        temp = yield gpio.i
        read2 |= (temp << i)
    assert read2 == read, f"Pad Sent: %x | GPIO Read: %x" % (data, read)
    # reset input signal
    yield pad.i.eq(0)
    yield Delay(delay)

"""
UART test function
Sends a byte via uart tx, checked at output pad
Then sends the same byte via input pad to uart rx
Input and output pads are different, so must specify both
"""
def uart_send(tx, rx, pad_tx, pad_rx, byte, delay=1e-6):
    # Drive uart tx - check the word seen at the Pad
    yield tx.oe.eq(1)
    yield tx.o.eq(1)
    yield Delay(2*delay)
    yield tx.o.eq(0) # start bit
    yield Delay(delay)
    read = 0
    # send one byte, lsb first
    for i in range(0, 8):
        bit = (byte >> i) & 0x1
        yield tx.o.eq(bit)
        yield Delay(delay)
        test_bit = yield pad_tx.o
        read |= (test_bit << i)
    yield tx.o.eq(1) # stop bit
    yield Delay(delay)
    assert byte == read, f"UART Sent: %x | Pad Read: %x" % (byte, read)
    # Drive Pad i - check word at uart rx
    yield pad_rx.i.eq(1)
    yield Delay(2*delay)
    yield pad_rx.i.eq(0) # start bit
    yield Delay(delay)
    read2 = 0
    for i in range(0, 8):
        bit = (read >> i) & 0x1
        yield pad_rx.i.eq(bit)
        yield Delay(delay)
        test_bit = yield rx
        read2 |= (test_bit << i)
    yield pad_rx.i.eq(1) # stop bit
    yield Delay(delay)
    assert read == read2, f"Pad Sent: %x | UART Read: %x" % (read, read2)

"""
I2C test function
Sends a byte via SDA.o (peripheral side), checked at output pad
Then sends the same byte via input pad to master SDA.i
This transaction doesn't make the distinction between read/write bit.
"""
def i2c_send(sda, scl, sda_pad, byte, delay=1e-6):
    # No checking yet
    # No pull-up on line implemented, set high instead
    yield sda.oe.eq(1)
    yield sda.o.eq(1)
    yield scl.oe.eq(1)
    yield scl.o.eq(1)
    yield sda_pad.i.eq(1)
    yield Delay(delay)
    read = 0
    yield sda.o.eq(0) # start bit
    yield Delay(delay)
    for i in range(0, 8):
        bit = (byte >> i) & 0x1
        yield sda.o.eq(bit)
        yield scl.o.eq(0)
        yield Delay(delay/2)
        yield scl.o.eq(1)
        temp = yield sda_pad.o
        read |= (temp << i)
        yield Delay(delay/2)
    yield sda.o.eq(1) # Master releases SDA line
    yield sda.oe.eq(0)
    assert byte == read, f"I2C Sent: %x | Pad Read: %x" % (byte, read)
    # Slave ACK
    yield sda_pad.i.eq(0)
    yield scl.o.eq(0)
    yield Delay(delay/2)
    yield scl.o.eq(1)
    yield Delay(delay/2)
    # Send byte back to master
    read2 = 0
    for i in range(0, 8):
        bit = (read >> i) & 0x1
        yield sda_pad.i.eq(bit)
        yield scl.o.eq(0)
        yield Delay(delay/2)
        yield scl.o.eq(1)
        temp = yield sda.i
        read2 |= (temp << i)
        yield Delay(delay/2)
    assert read == read2, f"Pad Sent: %x | I2C Read: %x" % (read, read2)
    # Master ACK
    yield sda.oe.eq(1)
    yield sda.o.eq(0)
    yield scl.o.eq(0)
    yield Delay(delay/2)
    yield scl.o.eq(1)
    yield Delay(delay/2)
    # Stop condition - SDA line high after SCL high
    yield scl.o.eq(0)
    yield Delay(delay/2)
    yield scl.o.eq(1)
    yield Delay(delay/2)
    yield sda.o.eq(1) # 'release' the SDA line

# Test the GPIO/UART/I2C connectivity
def test_man_pinmux(dut, requested):
    # TODO: Convert to automatic
    # [{"pad":%s, "bank":%d}, {"pad":%s, "bank":%d},...]
    #gpios = [{"padname":"N1", "bank":GPIO_BANK},
    #         {"padname":"N2", "bank":GPIO_BANK}]
    # [[txPAD, MUXx, rxPAD, MUXx],...] - diff banks not supported yet
    uarts = [{"txpadname":"N1", "rxpadname":"N2", "bank":UART_BANK}]
    # [[sdaPAD, MUXx, sclPAD, MUXx],...] - diff banks not supported yet
    i2cs = [{"sdapadname":"N1", "sclpadname":"N2", "bank":I2C_BANK}]

    gpios = []
    delay = 1e-6
    for pad in requested.keys():
        for mux in requested[pad].keys():
            periph = requested[pad][mux][0]

            if periph == "gpio":
                # [{"padname":%s, "bank": %d}, ...]
                gpios.append({"padname":pad, "bank": int(mux[3])})
            if periph == "uart":
                # TODO:
                pass
            if periph == "i2c":
                # TODO:
                pass
    print(gpios)
    # GPIO test
    for gpio_periph in gpios:
        padname = gpio_periph["padname"]
        gpio_bank = gpio_periph["bank"]
        gp = dut.pads[padname]["mux%d" % gpio_bank]
        pad = dut.pads[padname]["pad"]
        yield from set_bank(dut, gpio_bank)
        yield from gpio(gp, pad, 0x5a5)

    # UART test
    for uart_periph in uarts:
        txpadname = uart_periph["txpadname"]
        rxpadname = uart_periph["rxpadname"]
        uart_bank = uart_periph["bank"]
        tx = dut.pads[txpadname]["mux%d" % uart_bank]
        rx = dut.pads[rxpadname]["mux%d" % uart_bank]
        txpad = dut.pads[txpadname]["pad"]
        rxpad = dut.pads[rxpadname]["pad"]
        yield from set_bank(dut, UART_BANK)
        yield from uart_send(tx, rx, txpad, rxpad, 0x42)

    # I2C test
    for i2c_periph in i2cs:
        sdapadname = i2c_periph["sdapadname"]
        sclpadname = i2c_periph["sclpadname"]
        i2c_bank = i2c_periph["bank"]
        sda = dut.pads[sdapadname]["mux%d" % i2c_bank]
        scl = dut.pads[sclpadname]["mux%d" % i2c_bank]
        sdapad = dut.pads[sdapadname]["pad"]

    yield from set_bank(dut, I2C_BANK)
    yield from i2c_send(sda, scl, sdapad, 0x67)

def gen_gtkw_doc(module_name, requested, filename):
    # GTKWave doc generation
    style = {
        '': {'base': 'hex'},
        'in': {'color': 'orange'},
        'out': {'color': 'yellow'},
        'debug': {'module': 'top', 'color': 'red'}
    }
    # Create a trace list, each block expected to be a tuple()
    traces = []
    temp = 0
    n_banks = 0
    for pad in requested.keys():
        temp = len(requested[pad].keys())
        if n_banks < temp:
            n_banks = temp
        temp_traces = ("Pad %s" % pad, [])
        # Pad signals
        temp_traces[1].append(('%s__i' % pad, 'in'))
        temp_traces[1].append(('%s__o' % pad, 'out'))
        temp_traces[1].append(('%s__oe' % pad, 'out'))
        for mux in requested[pad].keys():
            periph = requested[pad][mux][0]
            unit_num = requested[pad][mux][1]
            if len(requested[pad][mux]) == 3:
                pin = requested[pad][mux][2]
            else:
                pin = "io"

            if periph == "gpio":
                temp_traces[1].append(('gp%d__i' % unit_num, 'in'))
                temp_traces[1].append(('gp%d__o' % unit_num, 'out'))
                temp_traces[1].append(('gp%d__oe' % unit_num, 'out'))
            elif periph == "uart":
                if pin == "tx":
                    temp_traces[1].append(('tx%d__o' % unit_num, 'out'))
                    temp_traces[1].append(('tx%d__oe' % unit_num, 'out'))
                    pass
                elif pin == "rx":
                    temp_traces[1].append(('rx%d' % unit_num, 'in'))
                    pass
            elif periph == "i2c":
                temp_traces[1].append(('%s%d__i' % (pin, unit_num), 'in'))
                temp_traces[1].append(('%s%d__o' % (pin, unit_num), 'out'))
                temp_traces[1].append(('%s%d__oe' % (pin, unit_num), 'out'))
        traces.append(temp_traces)

    # master bank signal
    temp_traces = ('Misc', [
                    ('bank[%d:0]' % ((n_banks-1).bit_length()-1), 'in')
                  ])
    traces.append(temp_traces)

    #print(traces)

    write_gtkw(filename+".gtkw", filename+".vcd", traces, style,
               module=module_name)


def sim_man_pinmux():
    filename = "test_man_pinmux"
    requested = {"N1": {"mux%d" % GPIO_BANK: ["gpio", 0],
                        "mux%d" % UART_BANK: ["uart", 0, "tx"],
                        "mux%d" % I2C_BANK: ["i2c", 0, "sda"]},
                 "N2": {"mux%d" % GPIO_BANK: ["gpio", 1],
                        "mux%d" % UART_BANK: ["uart", 0, "rx"],
                        "mux%d" % I2C_BANK: ["i2c", 0, "scl"]}
                }
    dut = ManPinmux(requested)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open(filename+".il", "w") as f:
        f.write(vl)

    m = Module()
    m.submodules.manpinmux = dut

    sim = Simulator(m)

    sim.add_process(wrap(test_man_pinmux(dut, requested)))
    sim_writer = sim.write_vcd(filename+".vcd")
    with sim_writer:
        sim.run()
    gen_gtkw_doc("top.manpinmux", dut.requested, filename)

if __name__ == '__main__':
    sim_man_pinmux()    
