from bsv.peripheral_gen.base import PBase


class sdmmc(PBase):

    def slowimport(self):
        return "    import sdcard_dummy              :: *;"

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self):
        return "        Ifc_sdcard_dummy sd{0} <-  mksdcard_dummy();"

    def _mk_connection(self, name=None, count=0):
        return "sd{0}.slave"

    def pinname_in(self, pname):
        return "%s_in" % pname

    def pinname_out(self, pname):
        if pname.startswith('d'):
            return "%s_out" % pname
        return pname

    def pinname_outen(self, pname):
        if pname.startswith('d'):
            return "%s_outen" % pname
