from bsv.peripheral_gen.mmcbase import MMCBase


class sdmmc(MMCBase):

    def slowimport(self):
        return "import sdcard_dummy              :: *;"

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self):
        return "Ifc_sdcard_dummy mmc{0} <-  mksdcard_dummy();"

    def _mk_connection(self, name=None, count=0):
        return "mmc{0}.slave"
