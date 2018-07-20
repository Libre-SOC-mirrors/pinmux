class PBase(object):
    pass

class UART(PBase):
    def importfn(self):
        return "          import Uart16550         :: *;"

    def ifacedecl(self):
        return "            interface RS232_PHY_Ifc uart{0}_coe;"


class RS232(PBase):
    def importfn(self):
        return "        import Uart_bs::*;\n" \
               "        import RS232_modified::*;"

    def ifacedecl(self):
        return "            interface RS232 uart{0}_coe;"


class spi(PBase):
    def importfn(self):
        return "        import I2C_top           :: *;"

    def ifacedecl(self):
        return "            interface I2C_out i2c{0}_out;"


class qspi(PBase):
    def importfn(self):
        return "        import qspi              :: *;"

    def ifacedecl(self):
        return "            interface QSPI_out qspi{0}_out;"


class pwm(PBase):
    def importfn(self):
        return "        interface PWMIO pwm_o;"

    def ifacedecl(self):
        return "        import pwm::*;"

