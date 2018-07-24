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
                }.get(pname, '')

    def pinname_outen(self, pname):
        return {'ck': 1,
                'nss': 1,
                }.get(pname, '')

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        ret = []
        plen = len(self.peripheral.pinspecs)
        template = "      mkConnection({0}.{1},\n\t\t\t{2}.{1});"
        ps = "pinmux.peripheral_side.%s" % name
        name = self.get_iname(count)
        n = "{0}.out".format(name)
        for ptype in ['io_out', 'io_out_en', 'io_in']:
            ret.append(template.format(ps, ptype, n))
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
