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

    def axi_slave_idx(self, idx, name, ifacenum):
        name = name.upper()
        return "typedef {0} {1}{2}_slave_num;".format(idx, name, ifacenum)


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


class PFactory(object):
    def getcls(self, name):
        return {'uart': uart,
                'rs232': rs232,
                'twi': twi,
                'qspi': qspi,
                'pwm': pwm,
                'gpio': gpio
                }.get(name, None)
