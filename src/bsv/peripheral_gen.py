class PBase(object):
    pass

    def axibase(self, name, ifacenum):
        name = name.upper()
        return "%(name)s%(ifacenum)dBase" % locals()

    def axiend(self, name, ifacenum):
        name = name.upper()
        return "%(name)s%(ifacenum)dEnd" % locals()

    def axi_reg_def(self, start, name, ifacenum):
        name = name.upper()
        offs = self.num_axi_regs32() * 4 * 16
        end = start + offs - 1
        bname = self.axibase(name, ifacenum)
        bend = self.axiend(name, ifacenum)
        comment = "%d 32-bit regs" % self.num_axi_regs32()
        return ("    `define%(bname)s 'h%(start)08X\n"
                "    `define%(bend)s  'h%(end)08X // %(comment)s" % locals(),
                offs)

    def axi_slave_name(self, name, ifacenum):
        name = name.upper()
        return "{0}{1}_slave_num".format(name, ifacenum)

    def axi_slave_idx(self, idx, name, ifacenum):
        name = self.axi_slave_name(name, ifacenum)
        return ("typedef {0} {1};".format(idx, name), 1)

    def axi_addr_map(self, name, ifacenum):
        bname = self.axibase(name, ifacenum)
        bend = self.axiend(name, ifacenum)
        name = self.axi_slave_name(name, ifacenum)
        return """\
        if(addr>=`{0} && addr<=`{1})
            return tuple2(True,fromInteger(valueOf({2})));
        else""".format(bname, bend, name)


class uart(PBase):
    def importfn(self):
        return "          import Uart16550         :: *;"

    def ifacedecl(self):
        return "            interface RS232_PHY_Ifc uart{0}_coe;\n" + \
               "            method Bit#(1) uart{0}_intr;"

    def num_axi_regs32(self):
        return 8


class rs232(PBase):
    def importfn(self):
        return "        import Uart_bs::*;\n" + \
               "        import RS232_modified::*;"

    def ifacedecl(self):
        return "            interface RS232 uart{0}_coe;"

    def num_axi_regs32(self):
        return 2


class twi(PBase):
    def importfn(self):
        return "        import I2C_top           :: *;"

    def ifacedecl(self):
        return "            interface I2C_out i2c{0}_out;\n" + \
               "            method Bit#(1) i2c{0}_isint;"

    def num_axi_regs32(self):
        return 8


class qspi(PBase):
    def importfn(self):
        return "        import qspi              :: *;"

    def ifacedecl(self):
        return "            interface QSPI_out qspi{0}_out;\n" + \
               "            method Bit#(1) qspi{0}_isint;"

    def num_axi_regs32(self):
        return 13


class pwm(PBase):
    def importfn(self):
        return "        import pwm::*;"

    def ifacedecl(self):
        return "        interface PWMIO pwm_o;"

    def num_axi_regs32(self):
        return 4


class gpio(PBase):
    def importfn(self):
        return "     import pinmux::*;\n" + \
               "     import mux::*;\n" + \
               "     import gpio::*;\n"

    def ifacedecl(self):
        return "        interface GPIO_config#({1}) pad_config{0};"

    def num_axi_regs32(self):
        return 2

    def axi_slave_idx(self, idx, name, ifacenum):
        """ generates AXI slave number definition, except
            GPIO also has a muxer per bank
        """
        name = name.upper()
        (ret, x) = PBase.axi_slave_idx(self, idx, name, ifacenum)
        (ret2, x) = PBase.axi_slave_idx(self, idx, "mux", ifacenum)
        return ("%s\n%s" % (ret, ret2), 2)


axi_slave_declarations = """\
typedef  0  SlowMaster;
{0}
typedef  TAdd#(LastGen_slave_num,`ifdef CLINT       1 `else 0 `endif )
              CLINT_slave_num;
typedef  TAdd#(CLINT_slave_num  ,`ifdef PLIC        1 `else 0 `endif )
              Plic_slave_num;
typedef  TAdd#(Plic_slave_num   ,`ifdef AXIEXP      1 `else 0 `endif )
              AxiExp1_slave_num;
typedef TAdd#(AxiExp1_slave_num,1) Num_Slow_Slaves;
"""


class PeripheralIface(object):
    def __init__(self, ifacename):
        self.slow = None
        slow = slowfactory.getcls(ifacename)
        if slow:
            self.slow = slow()

    def slowimport(self):
        if not self.slow:
            return ''
        return self.slow.importfn().format()

    def slowifdecl(self, count):
        if not self.slow:
            return ''
        return self.slow.ifacedecl().format(count, self.ifacename)

    def axi_reg_def(self, start, count):
        if not self.slow:
            return ('', 0)
        return self.slow.axi_reg_def(start, self.ifacename, count)

    def axi_slave_idx(self, start, count):
        if not self.slow:
            return ('', 0)
        return self.slow.axi_slave_idx(start, self.ifacename, count)

    def axi_addr_map(self, count):
        if not self.slow:
            return ''
        return self.slow.axi_addr_map(self.ifacename, count)

class PeripheralInterfaces(object):
    def __init__(self):
        pass

    def slowimport(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            ret.append(self.data[name].slowimport())
        return '\n'.join(list(filter(None, ret)))

    def slowifdecl(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                ret.append(self.data[name].slowifdecl(i))
        return '\n'.join(list(filter(None, ret)))

    def axi_reg_def(self, *args):
        ret = []
        start = 0x00011100  # start of AXI peripherals address
        for (name, count) in self.ifacecount:
            for i in range(count):
                x = self.data[name].axi_reg_def(start, i)
                print ("ifc", name, x)
                (rdef, offs) = x
                ret.append(rdef)
                start += offs
        return '\n'.join(list(filter(None, ret)))

    def axi_slave_idx(self, *args):
        ret = []
        start = 0
        for (name, count) in self.ifacecount:
            for i in range(count):
                (rdef, offs) = self.data[name].axi_slave_idx(start, i)
                print ("ifc", name, rdef, offs)
                ret.append(rdef)
                start += offs
        ret.append("typedef %d LastGen_slave_num" % (start - 1))
        decls = '\n'.join(list(filter(None, ret)))
        return axi_slave_declarations.format(decls)

    def axi_addr_map(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                ret.append(self.data[name].axi_addr_map(i))
        return '\n'.join(list(filter(None, ret)))


class PFactory(object):
    def getcls(self, name):
        return {'uart': uart,
                'rs232': rs232,
                'twi': twi,
                'qspi': qspi,
                'pwm': pwm,
                'gpio': gpio
                }.get(name, None)

slowfactory = PFactory()

