from bsv.peripheral_gen.mmcbase import MMCBase


class emmc(MMCBase):

    def slowimport(self):
        return "import emmc_dummy              :: *;"

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self):
        return "Ifc_emmc_dummy emmc{0} <-  mkemmc_dummy();"

    def _mk_connection(self, name=None, count=0):
        return "emmc{0}.slave"

