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

    def _mk_connection(self, name=None, count=0):
        return "lcd{0}.slave"

    def pinname_out(self, pname):
        if not pname.startswith('out'):
            return pname
        return ''

    def get_clock_reset(self, name, count):
        return "slow_clock, slow_reset"

    def _mk_pincon(self, name, count, ptyp):
        ret = [PBase._mk_pincon(self, name, count, ptyp)]
        if ptyp == 'fast':
            sname = self.get_iname(count)
            ps = "slow_peripherals.%s" % sname
        else:
            sname = self.peripheral.iname().format(count)
            ps = "pinmux.peripheral_side.%s" % sname
        name = self.get_iname(count)
        n = "{0}".format(name)
        for ptype in ['data_out']:
            ps_ = "{0}.{1}".format(ps, ptype)
            ret += self._mk_actual_connection('out', name, count, 'out',
                                              ptype, ps_, n, ptype)
        return '\n'.join(ret)

    def _mk_clk_con(self, name, count, ctype):
        ret = [PBase._mk_clk_con(self, name, count, ctype)]
        ck = self.get_clock_reset(name, count)
        if ck == PBase.get_clock_reset(self, name, count):
            return ret
        if ctype == 'slow':
            spc = "sp_clock, sp_reset"
        else:
            spc = "fast_clock, fast_reset"
        template = """\
Ifc_sync#({0}) {1}_sync <-mksyncconnection(
            {2}, {3});"""

        # one pin, data_out, might as well hard-code it
        typ = 'out'
        pname = 'data_out'
        n = name
        n_ = "{0}{1}".format(n, count)
        n_ = '{0}_{1}'.format(n_, pname)
        sz = len(self.peripheral.pinspecs) - 4  # subtract CK, DE, HS, VS
        ret.append(template.format("Bit#(%d)" % sz, n_, ck, spc))
        return '\n'.join(ret)
