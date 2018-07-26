from bsv.peripheral_gen.base import PBase


class flexbus(PBase):

    def slowimport(self):
        return "import FlexBus_Types::*;"

    def num_axi_regs32(self):
        return 0x4000000 # defines an entire memory range

    def extfastifinstance(self, name, count):
        return self._extifinstance(name, count, "_out", "", True,
                                   ".flexbus_side")

    def fastifdecl(self, name, count):
        return "interface FlexBus_Master_IFC fb{0}_out;".format(count)

    def mkfast_peripheral(self):
        return "AXI4_Slave_to_FlexBus_Master_Xactor_IFC " + \
               "#(`ADDR, `DATA, `USERSPACE)\n" + \
               "        fb{0} <- mkAXI4_Slave_to_FlexBus_Master_Xactor;"

    def _mk_connection(self, name=None, count=0):
        return "fb{0}.axi_side"

    def pinname_out(self, pname):
        if pname in ['cmd', 'clk']:
            return pname
        return ''

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
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
