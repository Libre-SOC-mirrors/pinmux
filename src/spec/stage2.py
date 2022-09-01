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

UART_BANK = 0
I2C_BANK = 1

"""
Really basic example, uart tx/rx and i2c sda/scl pinmux
"""
class ManPinmux(Elaboratable):
    def __init__(self):
        print("Test Manual Pinmux!")
        self.n_banks = 2
        self.iomux1 = IOMuxBlockSingle(self.n_banks)
        self.iomux2 = IOMuxBlockSingle(self.n_banks)
        self.pad1 = Record(name="Pad1", layout=io_layout)
        self.pad2 = Record(name="Pad2", layout=io_layout)
        self.uart = Record(name="uart", layout=uart_layout)
        self.i2c = {"sda": Record(name="sda", layout=io_layout),
                    "scl": Record(name="scl", layout=io_layout)
                   }
        self.bank = Signal(log2_int(self.n_banks))

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync
        iomux1 = self.iomux1
        iomux2 = self.iomux2
        m.submodules.iomux1 = iomux1
        m.submodules.iomux2 = iomux2

        pad1 = self.pad1
        pad2 = self.pad2
        uart = self.uart
        i2c = self.i2c
        bank = self.bank

        comb += iomux1.bank.eq(bank)
        comb += iomux2.bank.eq(bank)

        # uart connected to bank 0 - Pad 1 tx, Pad 2 rx
        comb += iomux1.bank_ports[UART_BANK].o.eq(uart.tx)
        comb += iomux1.bank_ports[UART_BANK].oe.eq(uart.oe)
        comb += uart.rx.eq(iomux2.bank_ports[UART_BANK].i)
        # i2c connected to bank 1 - Pad 1 sda, Pad 2 scl
        comb += iomux1.bank_ports[I2C_BANK].o.eq(i2c["sda"].o)
        comb += iomux1.bank_ports[I2C_BANK].oe.eq(i2c["sda"].oe)
        comb += i2c["sda"].i.eq(iomux1.bank_ports[I2C_BANK].i)
        comb += iomux2.bank_ports[I2C_BANK].o.eq(i2c["scl"].o)
        comb += iomux2.bank_ports[I2C_BANK].oe.eq(i2c["scl"].oe)
        comb += i2c["scl"].i.eq(iomux2.bank_ports[I2C_BANK].i)

        comb += pad1.o.eq(iomux1.out_port.o)
        comb += pad1.oe.eq(iomux1.out_port.oe)
        comb += iomux1.out_port.i.eq(pad1.i)
        comb += pad2.o.eq(iomux2.out_port.o)
        comb += pad2.oe.eq(iomux2.out_port.oe)
        comb += iomux2.out_port.i.eq(pad2.i)

        #temp for testing - connect pad rx-tx
        #comb += pad2.i.eq(pad1.o)

        return m

    def __iter__(self):
        for field in self.pad1.fields.values():
            yield field
        for field in self.pad2.fields.values():
            yield field
        for field in self.uart.fields.values():
            yield field
        for field in self.i2c["sda"].fields.values():
            yield field
        for field in self.i2c["scl"].fields.values():
            yield field
        yield self.bank

    def ports(self):
        return list(self)

def set_bank(dut, bank, delay=1e-6):
    yield dut.bank.eq(bank)
    yield Delay(delay)

def uart_send(tx, rx, byte, oe=None, delay=1e-6):
    if oe is not None:
        yield oe.eq(1)
    yield tx.eq(1)
    yield Delay(2*delay)
    yield tx.eq(0) # start bit
    yield Delay(delay)
    result = 0
    # send one byte, lsb first
    for i in range(0, 8):
        bit = (byte >> i) & 0x1
        yield tx.eq(bit)
        yield Delay(delay)
        test_bit = yield rx
        result |= (test_bit << i)
    yield tx.eq(1) # stop bit
    yield Delay(delay)
    if result == byte:
        print("Received: %x | Sent: %x" % (byte, result))
    else:
        print("Received: %x does NOT match sent: %x" % (byte, result))

def i2c_send(sda, scl, rx_sda, byte, delay=1e-6):
    # No checking yet
    # No pull-up on line implemented, set high instead
    yield sda.oe.eq(1)
    yield sda.o.eq(1)
    yield scl.oe.eq(1)
    yield scl.o.eq(1)
    yield rx_sda.eq(1)
    yield Delay(delay)
    yield sda.o.eq(0) # start bit
    yield Delay(delay)
    for i in range(0, 8):
        bit = (byte >> i) & 0x1
        yield sda.o.eq(bit)
        yield scl.o.eq(0)
        yield Delay(delay/2)
        yield scl.o.eq(1)
        yield Delay(delay/2)
    yield sda.o.eq(1) # Master releases SDA line
    yield sda.oe.eq(0)
    yield rx_sda.eq(0) # ACK
    yield Delay(delay)
    yield rx_sda.eq(1)



def test_man_pinmux(dut):
    delay = 1e-6
    # UART test
    yield from set_bank(dut, UART_BANK)
    yield from uart_send(dut.uart.tx, dut.pad1.o, 0x42, oe=dut.uart.oe)
    #yield dut.pad1.i.eq(1)
    yield from uart_send(dut.pad2.i, dut.uart.rx, 0x5A)
    yield dut.pad2.i.eq(0)
    yield Delay(delay)
    # I2C test
    yield from set_bank(dut, I2C_BANK)
    yield from i2c_send(dut.i2c['sda'], dut.i2c['scl'], dut.pad1.i, 0x67)


def sim_man_pinmux():
    filename = "test_man_pinmux"
    dut = ManPinmux()
    vl = rtlil.convert(dut, ports=dut.ports())
    with open(filename+".il", "w") as f:
        f.write(vl)

    m = Module()
    m.submodules.manpinmux = dut

    sim = Simulator(m)

    sim.add_process(wrap(test_man_pinmux(dut)))
    sim_writer = sim.write_vcd(filename+".vcd")
    with sim_writer:
        sim.run()
    #gen_gtkw_doc("top.manpinmux", dut.n_banks, filename)

if __name__ == '__main__':
    sim_man_pinmux()    
