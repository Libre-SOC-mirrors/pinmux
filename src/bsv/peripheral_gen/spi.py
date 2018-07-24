from bsv.peripheral_gen.base import PBase


class spi(PBase):

    def slowimport(self):
        return "    import qspi              :: *;"

    def slowifdecl(self):
        return "            interface QSPI_out spi{0}_out;\n" + \
               "            method Bit#(1) spi{0}_isint;"

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self):
        return "        Ifc_qspi spi{0} <-  mkqspi();"

    def _mk_connection(self, name=None, count=0):
        return "spi{0}.slave"

    def pinname_out(self, pname):
        return {'clk': 'out.clk_o',
                'nss': 'out.ncs_o',
                'mosi': 'out.io_o[0]',
                'miso': 'out.io_o[1]',
                }.get(pname, '')

    def pinname_outen(self, pname):
        return {'clk': 1,
                'nss': 1,
                'mosi': 'out.io_enable[0]',
                'miso': 'out.io_enable[1]',
                }.get(pname, '')

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        plen = len(self.peripheral.pinspecs)
        ret.append("    // XXX NSS and CLK are hard-coded master")
        ret.append("    // TODO: must add spi slave-mode")
        ret.append("    // all ins done in one rule from 4-bitfield")
        ret.append("    rule con_%s%d_io_in;" % (name, count))
        ret.append("       {0}{1}.out.io_i({{".format(name, count))
        for idx, pname in enumerate(['mosi', 'miso']):
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s_in" % sname
            ret.append("            {0},".format(ps))
        ret.append("            1'b0,1'b0")
        ret.append("        });")
        ret.append("    endrule")
        return '\n'.join(ret)

    def mk_ext_ifacedef(self, iname, inum):
        name = self.get_iname(inum)
        return "        method {0}_isint = {0}.interrupts[5];".format(name)

    def slowifdeclmux(self):
        return "        method Bit#(1) {1}{0}_isint;"
