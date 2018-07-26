from bsv.peripheral_gen.base import PBase


class pwm(PBase):

    def slowimport(self):
        return "import pwm::*;"

    def slowifdecl(self):
        return "interface PWMIO pwm{0}_io;"

    def num_axi_regs32(self):
        return 4

    def mkslow_peripheral(self, size=0):
        return "Ifc_PWM_bus pwm{0} <- mkPWM_bus(sp_clock);"

    def _mk_connection(self, name=None, count=0):
        return "pwm{0}.axi4_slave"

    def pinname_out(self, pname):
        return {'out': 'pwm_io.pwm_o'}.get(pname, '')
