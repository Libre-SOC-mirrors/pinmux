from bsv.peripheral_gen.base import PBase

class rgbttl(PBase):

    def slowimport(self):
        return "    import rgbttl_dummy              :: *;"

    def slowifdecl(self):
        return "            interface RGBTTL_out lcd{0}_out;"

    def num_axi_regs32(self):
        return 10

    def mkslow_peripheral(self):
        sz = len(self.peripheral.pinspecs) - 4 # subtract CK, DE, HS, VS
        return "        Ifc_rgbttl_dummy lcd{0} <-  mkrgbttl_dummy(%d);" % sz

    def _mk_connection(self, name=None, count=0):
        return "lcd{0}.slave"

    def pinname_out(self, pname):
        return pname
