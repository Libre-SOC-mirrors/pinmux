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
    def __init__(self, pad_names):
        print("Test Manual Pinmux!")
        self.n_banks = 4
        self.iomux1 = IOMuxBlockSingle(self.n_banks)
        self.iomux2 = IOMuxBlockSingle(self.n_banks)
        """
        self.pads = {}
        for pad in pad_names:
            self.pads[pad] = Record(name=pad, layout=io_layout)
        self.gpio = {"0": Record(name="gp0", layout=io_layout),
                     "1": Record(name="gp1", layout=io_layout)
                    }
        self.uart = Record(name="uart", layout=uart_layout)
        self.i2c = {"sda": Record(name="sda", layout=io_layout),
                    "scl": Record(name="scl", layout=io_layout)
                   }
        """
        self.bank = Signal(log2_int(self.n_banks))
        self.pads = {pad_names[0]:{}, pad_names[1]:{}}
        self.pads["N1"]["pad"] = Record(name=pad_names[0], layout=io_layout)
        self.pads["N1"]["mux%d" % GPIO_BANK] = Record(name="gp0",
                                                      layout=io_layout)
        self.pads["N1"]["mux%d" % UART_BANK] = Record(name="tx",
                                                      layout=uart_tx_layout)
        self.pads["N1"]["mux%d" % I2C_BANK] = Record(name="sda",
                                                     layout=io_layout)
        self.pads["N2"]["pad"] = Record(name=pad_names[1], layout=io_layout)
        self.pads["N2"]["mux%d" % GPIO_BANK] = Record(name="gp1",
                                                      layout=io_layout)
        self.pads["N2"]["mux%d" % UART_BANK] = Signal(name="rx") # One signal
        self.pads["N2"]["mux%d" % I2C_BANK] = Record(name="scl",
                                                     layout=io_layout)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync
        iomux1 = self.iomux1
        iomux2 = self.iomux2
        m.submodules.iomux1 = iomux1
        m.submodules.iomux2 = iomux2

        pads = self.pads
        pad0 = self.pads["N1"]["pad"]
        gp0 = self.pads["N1"]["mux%d" % GPIO_BANK]
        gp1 = self.pads["N2"]["mux%d" % GPIO_BANK]
        tx = self.pads["N1"]["mux%d" % UART_BANK]
        rx = self.pads["N2"]["mux%d" % UART_BANK]
        sda = self.pads["N1"]["mux%d" % I2C_BANK]
        scl = self.pads["N2"]["mux%d" % I2C_BANK]
        bank = self.bank

        comb += iomux1.bank.eq(bank)
        comb += iomux2.bank.eq(bank)

        # ---------------------------
        # This section is muxing only - doesn'care about pad names
        # ---------------------------
        # gpio - gpio0 on Pad1, gpio1 on Pad2
        comb += iomux1.bank_ports[GPIO_BANK].o.eq(gp0.o)
        comb += iomux1.bank_ports[GPIO_BANK].oe.eq(gp0.oe)
        comb += gp0.i.eq(iomux1.bank_ports[GPIO_BANK].i)
        comb += iomux2.bank_ports[GPIO_BANK].o.eq(gp1.o)
        comb += iomux2.bank_ports[GPIO_BANK].oe.eq(gp1.oe)
        comb += gp1.i.eq(iomux2.bank_ports[GPIO_BANK].i)
        # uart Pad 1 tx, Pad 2 rx
        comb += iomux1.bank_ports[UART_BANK].o.eq(tx.o)
        comb += iomux1.bank_ports[UART_BANK].oe.eq(tx.oe)
        comb += rx.eq(iomux2.bank_ports[UART_BANK].i)
        # i2c  Pad 1 sda, Pad 2 scl
        comb += iomux1.bank_ports[I2C_BANK].o.eq(sda.o)
        comb += iomux1.bank_ports[I2C_BANK].oe.eq(sda.oe)
        comb += sda.i.eq(iomux1.bank_ports[I2C_BANK].i)
        comb += iomux2.bank_ports[I2C_BANK].o.eq(scl.o)
        comb += iomux2.bank_ports[I2C_BANK].oe.eq(scl.oe)
        comb += scl.i.eq(iomux2.bank_ports[I2C_BANK].i)

        # ---------------------------
        # Here is where the muxes are assigned to the actual pads
        # ---------------------------
        # TODO: for-loop to autoconnect muxes to pads (n_pads var?)
        comb += pads['N1']["pad"].o.eq(iomux1.out_port.o)
        comb += pads['N1']["pad"].oe.eq(iomux1.out_port.oe)
        comb += iomux1.out_port.i.eq(pads['N1']["pad"].i)
        comb += pads['N2']["pad"].o.eq(iomux2.out_port.o)
        comb += pads['N2']["pad"].oe.eq(iomux2.out_port.oe)
        comb += iomux2.out_port.i.eq(pads['N2']["pad"].i)

        return m

    def __iter__(self):
        for pad in list(self.pads.keys()):
            for field in self.pads[pad]["pad"].fields.values():
                yield field
        #for field in self.uart.fields.values():
        #    yield field
        #for field in self.i2c["sda"].fields.values():
        #    yield field
        #for field in self.i2c["scl"].fields.values():
        #    yield field
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
def test_man_pinmux(dut, pad_names):
    delay = 1e-6
    # GPIO test
    yield from set_bank(dut, GPIO_BANK)
    yield from gpio(dut.pads["N1"]["mux%d" % GPIO_BANK],
                    dut.pads["N1"]["pad"], 0x5a5)
    yield from gpio(dut.pads["N2"]["mux%d" % GPIO_BANK],
                    dut.pads["N2"]["pad"], 0x5a5)
    # UART test
    yield from set_bank(dut, UART_BANK)
    yield from uart_send(dut.pads["N1"]["mux%d" % UART_BANK],
                         dut.pads["N2"]["mux%d" % UART_BANK],
                         dut.pads['N1']["pad"], dut.pads['N2']["pad"], 0x42)
    #yield dut.pads['N2'].i.eq(0)
    #yield Delay(delay)
    # I2C test
    yield from set_bank(dut, I2C_BANK)
    yield from i2c_send(dut.pads["N1"]["mux%d" % I2C_BANK],
                        dut.pads["N2"]["mux%d" % I2C_BANK],
                        dut.pads['N1']["pad"], 0x67)

def sim_man_pinmux():
    filename = "test_man_pinmux"
    pad_names = ["N1", "N2"]
    dut = ManPinmux(pad_names)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open(filename+".il", "w") as f:
        f.write(vl)

    m = Module()
    m.submodules.manpinmux = dut

    sim = Simulator(m)

    sim.add_process(wrap(test_man_pinmux(dut, pad_names)))
    sim_writer = sim.write_vcd(filename+".vcd")
    with sim_writer:
        sim.run()
    #gen_gtkw_doc("top.manpinmux", dut.n_banks, filename)

if __name__ == '__main__':
    sim_man_pinmux()    
