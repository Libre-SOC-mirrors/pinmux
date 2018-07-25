from bsv.peripheral_gen.base import PBase


class rgbttl(PBase):

    def slowimport(self):
        return "    import rgbttl_dummy              :: *;"

    def num_axi_regs32(self):
        return 10

    def mkslow_peripheral(self):
        sz = len(self.peripheral.pinspecs) - 4  # subtract CK, DE, HS, VS
        return "        Ifc_rgbttl_dummy lcd{0} <-  mkrgbttl_dummy();"

    def _mk_connection(self, name=None, count=0):
        return "lcd{0}.slave"

    def pinname_out(self, pname):
        if not pname.startswith('out'):
            return pname
        return ''

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        sname = self.peripheral.iname().format(count)
        plen = len(self.peripheral.pinspecs)
        template = "      mkConnection({0}.{1},\n\t\t\t{2}.{1});"
        name = self.get_iname(count)
        ps = "pinmux.peripheral_side.%s" % sname
        n = "{0}".format(name)
        for ptype in ['data_out']:
            ret.append(template.format(ps, ptype, n))
        return '\n'.join(ret)

    def slowifdeclmux(self, name, count):
        sname = self.get_iname(count)
        return "        interface PeripheralSideLCD %s;" % sname

