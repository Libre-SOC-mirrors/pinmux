from bsv.peripheral_gen.base import PBase


class rgbttl(PBase):

    def slowimport(self):
        return "import rgbttl_dummy              :: *;"

    def has_axi_master(self):
        return True

    def num_axi_regs32(self):
        return 10

    def mkfast_peripheral(self):
        sz = len(self.peripheral.pinspecs) - 4  # subtract CK, DE, HS, VS
        return "Ifc_rgbttl_dummy lcd{0} <-  mkrgbttl_dummy();"

    def _mk_connection(self, name=None, count=0, master=False):
        if master:
            return "lcd{0}.master"
        return "lcd{0}.slave"

    def pinname_out(self, pname):
        if not pname.startswith('out'):
            return pname
        return ''

    def get_clock_reset(self, name, count):
        return "slow_clock, slow_reset"

    def _mk_pincon(self, name, count, ptyp):
        ret = [PBase._mk_pincon(self, name, count, ptyp)]
        txt = self._mk_vpincon(name, count, ptyp, "out", "data_out")
        ret.append(txt)
        return '\n'.join(ret)

    def _mk_clk_con(self, name, count, ctype):
        ret = [PBase._mk_clk_con(self, name, count, ctype)]

        # data_out (hard-coded)
        sz = len(self.peripheral.pinspecs) - 4  # subtract CK, DE, HS, VS
        bitspec = "Bit#(%d)" % sz
        txt = self._mk_clk_vcon(name, count, ctype, "out", "data_out", bitspec)
        ret.append(txt)
        return '\n'.join(ret)
