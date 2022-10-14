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

from spec.iomux import IOMuxBlockSingle
from spec.base import PinSpec
from spec.jtag import iotypes
from spec.pinfunctions import pinspec

import code

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
GPIO_MUX = 0
UART_MUX = 1
I2C_MUX = 2

"""
Really basic example, uart tx/rx and i2c sda/scl pinmux
"""
class ManPinmux(Elaboratable):
    def __init__(self, ps):
        print("Test Manual Pinmux!")
        self.gen_pinmux_dict(ps)

        self.pads = {}

        print("--------------------")
        # Automatically create the necessary periph/pad Records/Signals
        # depending on the given dict specification
        for pad in self.requested.keys():
            self.pads[pad] = {}
            self.pads[pad]["pad"] = Record(name=pad, layout=io_layout)
            self.pads[pad]["n_ports"] = len(self.requested[pad])
            if self.pads[pad]["n_ports"] == 1:
                pass # skip mux creation
            else:
                print(self.pads[pad]["n_ports"])
                # Need to determine num of bits - to make number a pow of 2
                portsize = self.pads[pad]["n_ports"].bit_length()
                self.pads[pad]["port"] = Signal(portsize, name="%s_port" % (pad))
                self.muxes[pad] = IOMuxBlockSingle(self.pads[pad]["n_ports"])
            for mux in self.requested[pad].keys():
                periph = self.requested[pad][mux]["periph"]
                suffix = self.requested[pad][mux]["suffix"]
                sig = self.requested[pad][mux]["signal"][:-1]
                sig_type = iotypes[self.requested[pad][mux]["signal"][-1]]
                #print(sig, sig_type)
                if sig_type == iotypes['*']:
                    self.pads[pad][mux] = Record(name="%s%s" % (sig, suffix),
                                                 layout=io_layout)
                elif sig_type == iotypes['+']:
                    self.pads[pad][mux] = Signal(name="%s%s_o" % (sig, suffix))
                elif sig_type == iotypes['-']:
                    self.pads[pad][mux] = Signal(name="%s%s_i" % (sig, suffix))
        print(self.pads)

    def elaborate(self, platform):
        m = Module()
        comb, sync = m.d.comb, m.d.sync
        muxes = self.muxes
        pads = self.pads
        for pad in pads.keys():
            if len(self.requested[pad]) == 1:
                pass
            else:
                port = self.pads[pad]["port"]
                m.submodules[pad+"_mux"] = muxes[pad]
                # TODO: all muxes controlled by the same multi-bit signal
                comb += muxes[pad].port.eq(port)

        # print(self.requested)
        # print(self.pads)

        # ---------------------------
        # This section connects the periphs to the assigned ports
        # ---------------------------
        for pad in pads.keys():
            if len(self.requested[pad]) == 1:
                # connect directly
                mux = 0 # assume only port0 has been defined
                print(self.requested[pad])
                periph = self.requested[pad][mux]["periph"]
                #suffix = self.requested[pad][mux]["suffix"]
                sig = self.requested[pad][mux]["signal"][:-1]
                sig_type = iotypes[self.requested[pad][mux]["signal"][-1]]
                if sig_type == iotypes['*']:
                    comb += pads[pad]["pad"].o.eq(pads[pad][mux].o)
                    comb += pads[pad]["pad"].oe.eq(pads[pad][mux].oe)
                    comb += pads[pad][mux].i.eq(pads[pad]["pad"].i)
                elif sig_type == iotypes['+']:
                    comb += pads[pad]["pad"].o.eq(pads[pad][mux].o)
                elif sig_type == iotypes['-']:
                    comb += pads[pad][mux].i.eq(pads[pad]["pad"].i)
            else:
                for mux in self.requested[pad].keys():
                    periph = self.requested[pad][mux]["periph"]
                    #suffix = self.requested[pad][mux]["suffix"]
                    sig = self.requested[pad][mux]["signal"][:-1]
                    sig_type = iotypes[self.requested[pad][mux]["signal"][-1]]
                    num = int(mux)
                    print(pad, mux, sig, sig_type)
                    print(len(muxes[pad].periph_ports))
                    if sig_type == iotypes['*']:
                        comb += muxes[pad].periph_ports[num].o.eq(
                                                             pads[pad][mux].o)
                        comb += muxes[pad].periph_ports[num].oe.eq(
                                                             pads[pad][mux].oe)
                        comb += pads[pad][mux].i.eq(
                                               muxes[pad].periph_ports[num].i)
                    elif sig_type == iotypes['+']:
                        comb += muxes[pad].periph_ports[num].o.eq(
                                                             pads[pad][mux])
                    elif sig_type == iotypes['-']:
                        comb += pads[pad][mux].eq(
                                               muxes[pad].periph_ports[num].i)
        # ---------------------------
        # Here is where the muxes are assigned to the actual pads
        # ---------------------------
        for pad in pads.keys():
            if len(self.requested[pad]) == 1:
                pass # if only one periph, no mux present
            else:
                comb += pads[pad]["pad"].o.eq(muxes[pad].out_port.o)
                comb += pads[pad]["pad"].oe.eq(muxes[pad].out_port.oe)
                comb += muxes[pad].out_port.i.eq(pads[pad]["pad"].i)

        return m

    def __iter__(self):
        print("=============")
        print(self.pads)
        print("=============")
        for pad in list(self.pads.keys()):
            for field in self.pads[pad]["pad"].fields.values():
                yield field
            for mux in self.pads[pad].keys():
                print(type(self.pads[pad][mux]))
                print(pad, mux, self.pads[pad][mux])
                if type(self.pads[pad][mux]) == Signal:
                    yield self.pads[pad][mux]
                elif type(self.pads[pad][mux]) == Record:
                    for field in self.pads[pad][mux].fields.values():
                        yield field
                else:
                    print("%s is a var, not Sig/Rec, skipping!" % mux)

    def ports(self):
        return list(self)

    def gen_pinmux_dict(self, ps, write_file=False):
        if write_file:
            with open("test.mdwn", "w") as of:
                pinout, bankspec, pin_spec, fixedpins = ps.write(of)
        #print(ps.items())
        #print(ps.byspec)
        #print(ps.fnspec)
        # TODO: get from ps
        self.requested = {}
        self.muxes = {}

        # Create local list of peripheral names defined in pinfunctions.py
        defined_func = []
        for pfunc in pinspec:
            defined_func.append(pfunc[0])

        for pin in ps.items():
            pin_no = pin[0]
            for mux in pin[1].keys():
                bank = pin[1][mux][1]
                signal_str = pin[1][mux][0]
                pad = "%s%d" % (bank, pin_no)
                # Get the signal name prefix
                index_under = signal_str.find('_')
                """
                periph format: [periph+suffix]
                GPIO periph format: [periph+bank+suffix]
                Problem is that GPIO has a different suffix to UART/TWI.
                Assuming that other peripherals may have their own name formats.
                keep stripping last chars from string until remainder matches
                one of the existing peripheral names
                probably very inefficient...
                NO ERROR CHECKING
                """
                periph = signal_str[:index_under]
                func = signal_str[index_under+1:]
                while periph != '':
                    if periph in defined_func:
                        break # Found valid periph
                    periph = periph.rstrip(periph[-1])

                # flag for peripheral string, needed as GPIO has a diff format
                # to UART and TWI, TODO: may need to check for other periph
                if periph == "GPIO":
                    check_string = periph + bank
                else:
                    check_string = periph

                # Find the suffix for the specified periph/pin
                suffix = ''
                for a in ps.fnspec.items():
                    for key in a[1]:
                        if check_string in key:
                            print(key, a[1][key])
                            suffix = a[1][key].suffix
                        else:
                            continue

                # key to use in PinSpec.byspec has format: [perith+':'+suffix]
                # need to get the suffix from Pin object
                #index = len(periph)
                #print(signal_str[index:index_under])
                signal = ''
                for sig_spec in ps.byspec[periph+':'+suffix]:
                    if func in sig_spec:
                        signal = sig_spec
                #suffix = ps.fnspec[fnspec_key][fnspec_key]
                print(pad, signal_str, signal_str[:index_under],
                      periph, func, suffix, signal, mux)
                print("Now adding to internal pinmux dict")
                if not (pad in self.requested.keys()):
                    self.requested[pad] = {}
                self.requested[pad][mux] = {"periph":periph, "suffix":suffix,
                                            "signal":signal}
        print(self.requested)

def set_port(dut, pad, port, delay=1e-6):
    if dut.pads[pad]["n_ports"] == 1:
        print("Pad %s only has one function, skipping setting mux!" % pad)
    else:
        yield dut.pads[pad]["port"].eq(port)
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
    print(type(tx))
    #yield tx.oe.eq(1)
    yield tx.eq(1)
    yield Delay(2*delay)
    yield tx.eq(0) # start bit
    yield Delay(delay)
    read = 0
    # send one byte, lsb first
    for i in range(0, 8):
        bit = (byte >> i) & 0x1
        yield tx.eq(bit)
        yield Delay(delay)
        test_bit = yield pad_tx.o
        read |= (test_bit << i)
    yield tx.eq(1) # stop bit
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
def test_man_pinmux(dut):
    requested = dut.requested
    # TODO: Convert to automatic
    # [{"pad":%s, "port":%d}, {"pad":%s, "port":%d},...]
    #gpios = [{"padname":"N1", "port":GPIO_MUX},
    #         {"padname":"N2", "port":GPIO_MUX}]
    # [[txPAD, MUXx, rxPAD, MUXx],...] - diff ports not supported yet
    #uarts = [{"txpadname":"N1", "rxpadname":"N2", "mux":UART_MUX}]
    uarts = {}
    # [[sdaPAD, MUXx, sclPAD, MUXx],...] - diff ports not supported yet
    #i2cs = [{"sdapadname":"N1", "sclpadname":"N2", "mux":I2C_MUX}]
    i2cs = {}

    gpios = []
    delay = 1e-6
    for pad in requested.keys():
        for mux in requested[pad].keys():
            periph = requested[pad][mux]["periph"]
            suffix = requested[pad][mux]["suffix"]
            if periph == "GPIO":
                # [{"padname":%s, "port": %d}, ...]
                gpios.append({"padname":pad, "mux": mux})
            if periph == "UART":
                # Make sure dict exists
                if not (suffix in uarts.keys()):
                    uarts[suffix] = {}

                if requested[pad][mux]["signal"][:-1] == "TX":
                    uarts[suffix]["txpadname"] = pad
                    uarts[suffix]["txmux"] = mux
                elif requested[pad][mux]["signal"][:-1] == "RX":
                    uarts[suffix]["rxpadname"] = pad
                    uarts[suffix]["rxmux"] = mux
            if periph == "TWI":
                if not (suffix in i2cs.keys()):
                    i2cs[suffix] = {}
                if requested[pad][mux]["signal"][:-1] == "SDA":
                    i2cs[suffix]["sdapadname"] = pad
                    i2cs[suffix]["sdamux"] = mux
                elif requested[pad][mux]["signal"][:-1] == "SCL":
                    i2cs[suffix]["sclpadname"] = pad
                    i2cs[suffix]["sclmux"] = mux
    print(gpios)
    print(uarts)
    print(i2cs)

    # GPIO test
    for gpio_periph in gpios:
        padname = gpio_periph["padname"]
        gpio_port = gpio_periph["mux"]
        gp = dut.pads[padname][gpio_port]
        pad = dut.pads[padname]["pad"]
        yield from set_port(dut, padname, gpio_port)
        yield from gpio(gp, pad, 0x5a5)

    # UART test
    for suffix in uarts.keys():
        txpadname = uarts[suffix]["txpadname"]
        rxpadname = uarts[suffix]["rxpadname"]
        txport = uarts[suffix]["txmux"]
        rxport = uarts[suffix]["rxmux"]
        tx = dut.pads[txpadname][txport]
        rx = dut.pads[rxpadname][rxport]
        txpad = dut.pads[txpadname]["pad"]
        rxpad = dut.pads[rxpadname]["pad"]
        yield from set_port(dut, txpadname, txport)
        yield from set_port(dut, rxpadname, rxport)
        yield from uart_send(tx, rx, txpad, rxpad, 0x42)

    # I2C test
    for suffix in i2cs.keys():
        sdapadname = i2cs[suffix]["sdapadname"]
        sclpadname = i2cs[suffix]["sclpadname"]
        sdaport = i2cs[suffix]["sdamux"]
        sclport = i2cs[suffix]["sclmux"]
        sda = dut.pads[sdapadname][sdaport]
        scl = dut.pads[sclpadname][sclport]
        sdapad = dut.pads[sdapadname]["pad"]
        yield from set_port(dut, sdapadname, sdaport)
        yield from set_port(dut, sclpadname, sclport)
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
    n_ports = 0
    for pad in requested.keys():
        temp = len(requested[pad].keys())
        if n_ports < temp:
            n_ports = temp
        temp_traces = ("Pad %s" % pad, [])
        # Pad signals
        temp_traces[1].append(('%s__i' % pad, 'in'))
        temp_traces[1].append(('%s__o' % pad, 'out'))
        temp_traces[1].append(('%s__oe' % pad, 'out'))
        # Port signal
        temp_traces[1].append(('%s_port[%d:0]'
                               % (pad, (n_ports-1).bit_length()-1), 'in'))

        traces.append(temp_traces)
        temp_traces = ("Pad %s Peripherals" % pad, [])
        for mux in requested[pad].keys():
            periph = requested[pad][mux]["periph"]
            suffix = requested[pad][mux]["suffix"]
            # TODO: cleanup
            pin = requested[pad][mux]["signal"][:-1]

            sig_type = iotypes[requested[pad][mux]["signal"][-1]]
            #print(sig, sig_type)
            if periph == "GPIO":
                name_format = "%s%s" % (pin, suffix)
            else:
                name_format = "%s%s" % (pin, suffix)
            if sig_type == iotypes['*']:
                temp_traces[1].append(('%s__i' % name_format, 'in'))
                temp_traces[1].append(('%s__o' % name_format, 'out'))
                temp_traces[1].append(('%s__oe' % name_format, 'out'))
            # Single underscore because Signal, not Record
            if sig_type == iotypes['+']:
                temp_traces[1].append(('%s_o' % name_format, 'out'))
            if sig_type == iotypes['-']:
                temp_traces[1].append(('%s_i' % name_format, 'in'))
        traces.append(temp_traces)

    #print(traces)

    write_gtkw(filename+".gtkw", filename+".vcd", traces, style,
               module=module_name)


def sim_man_pinmux(ps):
    filename = "test_man_pinmux"
    """
    requested = {"N1": {"mux%d" % GPIO_MUX: ["gpio", 0, '0*'],
                        "mux%d" % UART_MUX: ["uart", 0, 'tx+'],
                        "mux%d" % I2C_MUX: ["i2c", 0, 'sda*']},
                 "N2": {"mux%d" % GPIO_MUX: ["gpio", 1, '*'],
                        "mux%d" % UART_MUX: ["uart", 0, 'rx-'],
                        "mux%d" % I2C_MUX: ["i2c", 0, 'scl*']},
                 "N3": {"mux%d" % GPIO_MUX: ["gpio", 2, '0*']},
                 "N4": {"mux%d" % GPIO_MUX: ["gpio", 3, '0*']}
                }
    """
    dut = ManPinmux(ps)
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
    gen_gtkw_doc("top.manpinmux", dut.requested, filename)


if __name__ == '__main__':
    #pinbanks = []
    #fixedpins = []
    #function_names = []
    #testspec = PinSpec()
    pinbanks = {
        'A': (4, 4), # bankname: (num of pins, muxwidth)
        'B': (2, 4),
        #'C': (24, 1),
        #'D': (93, 1),
    }
    fixedpins = {
        'POWER_GPIO': [
            'VDD_GPIOB',
            'GND_GPIOB',
        ]}
    function_names = {'TWI0': 'I2C 0',
                      'UART0': 'UART (TX/RX) 0',
                     }
    ps = PinSpec(pinbanks, fixedpins, function_names)
    # Unit number, (Bank, pin #), mux, start, num # pins
    ps.gpio("", ('A', 0), 0, 0, 4)
    ps.gpio("2", ('B', 0), 0, 0, 2)
    ps.uart("0", ('A', 0), 1)
    ps.i2c("0", ('A', 0), 2)
    sim_man_pinmux(ps)

    """
    desc_dict_keys = ['UART0', 'TWI0', 'GPIOA_A0', 'GPIOA_A1', 'GPIOA_A2',
                      'GPIOA_A3']
    eint = []
    pwm = []
    desc = {'UART0': 'Basic serial TX/RX serial port',
            'TWI0': 'I2C interface',
            'GPIOA_A0': 'Test GPIO0',
            'GPIOA_A1': 'Test GPIO1',
            'GPIOA_A2': 'Test GPIO2',
            'GPIOA_A3': 'Test GPIO3'}
    ps.add_scenario("Test Manual Pinmux", desc_dict_keys, eint, pwm, desc)
    """
    #gen_pinmux_dict(ps)
    #code.interact(local=locals())
