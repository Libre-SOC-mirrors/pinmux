from bsv.peripheral_gen.base import PBase


class sdram(PBase):

    def slowimport(self):
        return "import sdr_top::*;"

    def num_axi_regs32(self):
        return 0x400000  # defines an entire memory range

    def extfastifinstance(self, name, count):
        return "// TODO" + self._extifinstance(name, count, "_out", "", True,
                                   ".if_sdram_out")

    def fastifdecl(self, name, count):
        return "// (*always_ready*) interface " + \
                "Ifc_sdram_out sdr{0}_out;".format(count)

    def get_clock_reset(self, name, count):
        return "slow_clock, slow_reset"

    def mkfast_peripheral(self):
        return "Ifc_sdr_slave sdr{0} <- mksdr_axi4_slave(clk0);"

    def _mk_connection(self, name=None, count=0):
        return ["sdr{0}.axi4_slave_sdram",
                "sdr{0}.axi4_slave_cntrl_reg"]
                

    def pinname_in(self, pname):
        return {'ta': 'sdram_side.m_tAn',
                }.get(pname, '')

    def pinname_out(self, pname):
        return {'ale': 'sdram_side.m_ALE',
                'oe': 'sdram_side.m_OEn',
                'tbst': 'sdram_side.m_TBSTn',
                'rw': 'sdram_side.m_R_Wn',
                }.get(pname, '')

    def _mk_clk_con(self, name, count, ctype):
        ret = [PBase._mk_clk_con(self, name, count, ctype)]
        for pname, sz, ptype in [
            ('cs', 6, 'out'),
            ('bwe', 4, 'out'),
            ('tsiz', 2, 'out'),
            ('ad_out', 32, 'out'),
            ('ad_in', 32, 'in'),
            ('ad_out_en', 32, 'out'),
        ]:
            bitspec = "Bit#(%d)" % sz
            txt = self._mk_clk_vcon(name, count, ctype, ptype, pname, bitspec)
            ret.append(txt)
        return '\n'.join(ret)

    def _mk_pincon(self, name, count, typ):
        ret = [PBase._mk_pincon(self, name, count, typ)]
        assert typ == 'fast' # TODO slow?
        for pname, stype, ptype in [
            ('cs', 'm_FBCSn', 'out'),
            ('bwe', 'm_BWEn', 'out'),
            ('tsiz', 'm_TSIZ', 'out'),
            ('ad_out', 'm_AD', 'out'),
            ('ad_in', 'm_din', 'in'),
            ('ad_out_en', 'm_OE32n', 'out'),
        ]:
            ret.append(self._mk_vpincon(name, count, typ, ptype, pname,
                                        "sdram_side.{0}".format(stype)))

        return '\n'.join(ret)
