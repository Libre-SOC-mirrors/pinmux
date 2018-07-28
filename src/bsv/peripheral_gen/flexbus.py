from bsv.peripheral_gen.base import PBase


class flexbus(PBase):

    def slowimport(self):
        return "import FlexBus_Types::*;"

    def num_axi_regs32(self):
        return 0x4000000  # defines an entire memory range

    def extfastifinstance(self, name, count):
        return self._extifinstance(name, count, "_out", "", True,
                                   ".flexbus_side")

    def fastifdecl(self, name, count):
        return "interface FlexBus_Master_IFC fb{0}_out;".format(count)

    def mkfast_peripheral(self):
        return "AXI4_Slave_to_FlexBus_Master_Xactor_IFC " + \
               "#(`PADDR, `DATA, `USERSPACE)\n" + \
               "        fb{0} <- mkAXI4_Slave_to_FlexBus_Master_Xactor;"

    def _mk_connection(self, name=None, count=0):
        return "fb{0}.axi_side"

    def pinname_in(self, pname):
        return {'ta': 'flexbus_side.tAn',
                }.get(pname, '')

    def pinname_out(self, pname):
        return {'ale': 'flexbus_side.m_ALE',
                'oe': 'flexbus_side.m_OEn',
                'rw': 'flexbus_side.m_R_Wn',
                }.get(pname, '')

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        plen = len(self.peripheral.pinspecs)
        template = "mkConnection({0}.{3},\n\t\t\t{2}.flexbus_side.{1});"
        sname = self.peripheral.iname().format(count)
        name = self.get_iname(count)
        ps = "pinmux.peripheral_side.%s" % sname
        n = "{0}".format(name)
        for stype, ptype in [
            ('cs', 'm_FBCSn'),
            ('bwe', 'm_BWEn'),
            ('tbst', 'm_TBSTn'),
            ('tsiz', 'm_TSIZ'),
            ('ad_in', 'm_AD'),
            ('ad_out', 'm_din'),
            ('ad_en', 'm_OE32n'),
        ]:
            ret.append(template.format(ps, ptype, n, stype))
        return '\n'.join(ret)
