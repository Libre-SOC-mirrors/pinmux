from bsv.peripheral_gen.base import PBase


class sdmmc(PBase):

    def slowimport(self):
        return "import sdcard_dummy              :: *;"

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self):
        return "Ifc_sdcard_dummy sd{0} <-  mksdcard_dummy();"

    def _mk_connection(self, name=None, count=0):
        return "sd{0}.slave"

    def pinname_out(self, pname):
        if pname in ['cmd', 'clk']:
            return pname
        return ''

    def _mk_pincon(self, name, count, typ):
        assert typ == 'slow', "TODO: mkConnection for fast"
        ret = [PBase._mk_pincon(self, name, count, typ)]
        # special-case for gpio in, store in a temporary vector
        plen = len(self.peripheral.pinspecs)
        template = "mkConnection({0}.{1},\n\t\t\t{2}.{1});"
        sname = self.peripheral.iname().format(count)
        name = self.get_iname(count)
        ps = "pinmux.peripheral_side.%s" % sname
        n = "{0}".format(name)
        for ptype in ['out', 'out_en', 'in']:
            ret.append(template.format(ps, ptype, n))
        return '\n'.join(ret)
