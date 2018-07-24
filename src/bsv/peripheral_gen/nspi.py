from bsv.peripheral_gen.base import PBase


class nspi(PBase):

    def __init__(self, name):
        PBase.__init__(self, name)
        self.ifndict = {'N': name.upper(), 'n': name}

    def slowimport(self):
        return "    import %(n)s              :: *;" % self.ifndict

    def slowifdecl(self):
        return "            interface %(N)s_out %(n)s{0}_out;\n" + \
               "            method Bit#(1) %(n)s{0}_isint;" % self.ifndict

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self, size=0):
        return "        Ifc_%(n)s %(n)s{0} <-  mk%(n)s();" % self.ifndict

    def _mk_connection(self, name=None, count=0):
        return "%(n)s{0}.slave" % self.ifndict

    def pinname_out(self, pname):
        return {'ck': 'out.clk_o',
                'nss': 'out.ncs_o',
                }.get(pname, '')

    def __disable_pinname_outen(self, pname):
        return {'ck': 1,
                'nss': 1,
                }.get(pname, '')

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        plen = len(self.peripheral.pinspecs)
        template = "      mkConnection({0}.{1},\n\t\t\t{2}.{1});"
        sname = self.peripheral.iname().format(count)
        name = self.get_iname(count)
        ps = "pinmux.peripheral_side.%s" % sname
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

    def slowifdeclmux(self, name, count):
        sname = self.get_iname(count)
        return "        method Bit#(1) %s_isint;" % sname
