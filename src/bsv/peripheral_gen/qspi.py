from bsv.peripheral_gen.base import PBase


class qspi(PBase):

    def slowimport(self):
        return "    import qspi              :: *;"

    def slowifdecl(self):
        return "            interface QSPI_out qspi{0}_out;\n" + \
               "            method Bit#(1) qspi{0}_isint;"

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self, size=0):
        return "        Ifc_qspi qspi{0} <-  mkqspi();"

    def _mk_connection(self, name=None, count=0):
        return "qspi{0}.slave"

    def pinname_out(self, pname):
        return {'ck': 'out.clk_o',
                'nss': 'out.ncs_o',
                'io0': 'out.io_o[0]',
                'io1': 'out.io_o[1]',
                'io2': 'out.io_o[2]',
                'io3': 'out.io_o[3]',
                }.get(pname, '')

    def pinname_outen(self, pname):
        return {'ck': 1,
                'nss': 1,
                'io0': 'out.io_enable[0]',
                'io1': 'out.io_enable[1]',
                'io2': 'out.io_enable[2]',
                'io3': 'out.io_enable[3]',
                }.get(pname, '')

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        plen = len(self.peripheral.pinspecs)
        ret.append("    // XXX NSS and CLK are hard-coded master")
        ret.append("    // TODO: must add qspi slave-mode")
        ret.append("    // all ins done in one rule from 4-bitfield")
        ret.append("    rule con_%s%d_io_in;" % (name, count))
        ret.append("       {0}{1}.out.io_i({{".format(name, count))
        for i, p in enumerate(self.peripheral.pinspecs):
            typ = p['type']
            pname = p['name']
            if not pname.startswith('io'):
                continue
            idx = pname[1:]
            n = name
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s_in" % sname
            comma = '' if i == 5 else ','
            ret.append("            {0}{1}".format(ps, comma))
        ret.append("        });")
        ret.append("    endrule")
        return '\n'.join(ret)

    def num_irqs(self):
        return 6

    def plic_object(self, pname, idx):
        return "{0}.interrupts()[{1}]".format(pname, idx)

    def mk_ext_ifacedef(self, iname, inum):
        name = self.get_iname(inum)
        return "        method {0}_isint = {0}.interrupts[5];".format(name)

    def slowifdeclmux(self):
        return "        method Bit#(1) {1}{0}_isint;"
