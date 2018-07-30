from bsv.peripheral_gen.base import PBase


class flexbus(PBase):

    def slowimport(self):
        return "import FlexBus_Types::*;"

    def num_axi_regs32(self):
        return 0x400000  # defines an entire memory range

    def extfastifinstance(self, name, count):
        return self._extifinstance(name, count, "_out", "", True,
                                   ".flexbus_side")

    def get_clock_reset(self, name, count):
        return "slow_clock, slow_reset"

    def fastifdecl(self, name, count):
        return "interface FlexBus_Master_IFC fb{0}_out;".format(count)

    def mkfast_peripheral(self):
        return "AXI4_Slave_to_FlexBus_Master_Xactor_IFC " + \
               "#(`PADDR, `DATA, `USERSPACE)\n" + \
               "        fb{0} <- mkAXI4_Slave_to_FlexBus_Master_Xactor;"

    def _mk_connection(self, name=None, count=0):
        return "fb{0}.axi_side"

    def pinname_in(self, pname):
        return {'ta': 'flexbus_side.m_tAn',
                }.get(pname, '')

    def pinname_out(self, pname):
        return {'ale': 'flexbus_side.m_ALE',
                'oe': 'flexbus_side.m_OEn',
                'tbst': 'flexbus_side.m_TBSTn',
                'rw': 'flexbus_side.m_R_Wn',
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
                                        "flexbus_side.{0}".format(stype)))

        return '\n'.join(ret)
