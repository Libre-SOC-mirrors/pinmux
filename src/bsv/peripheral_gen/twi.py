from bsv.peripheral_gen.base import PBase


class twi(PBase):

    def slowimport(self):
        return "import I2C_top           :: *;"

    def irq_name(self):
        return "twi{0}_isint"

    def slowifdecl(self):
        return "interface I2C_out twi{0}_out;\n" + \
               "method Bit#(1) %s;" % self.irq_name()

    def num_axi_regs32(self):
        return 8

    def mkslow_peripheral(self, size=0):
        return "I2C_IFC twi{0} <- mkI2CController();"

    def _mk_connection(self, name=None, count=0):
        return "twi{0}.slave_i2c_axi"

    def pinname_out(self, pname):
        return {'sda': 'out.sda_out',
                'scl': 'out.scl_out'}.get(pname, '')

    def pinname_in(self, pname):
        return {'sda': 'out.sda_in',
                'scl': 'out.scl_in'}.get(pname, '')

    def pinname_outen(self, pname):
        return {'sda': 'out.sda_out_en',
                'scl': 'out.scl_out_en'}.get(pname, '')

    def num_irqs(self):
        return 3

    def plic_object(self, pname, idx):
        return ["{0}.isint()",
                "{0}.timerint()",
                "{0}.isber()"
                ][idx].format(pname)

    def mk_ext_ifacedef(self, iname, inum):
        name = self.get_iname(inum)
        return "method {0}_isint = {0}.isint;".format(name)

    def slowifdeclmux(self, name, inum):
        sname = self.get_iname(inum)
        return "method Bit#(1) %s_isint;" % sname
