class PBase(object):
    pass

class uart(PBase):
    def importfn(self):
        return "          import Uart16550         :: *;"

    def ifacedecl(self):
        return "            interface RS232_PHY_Ifc uart{0}_coe;" \
               "            method Bit#(1) uart{0}_intr;"


class rs232(PBase):
    def importfn(self):
        return "        import Uart_bs::*;\n" \
               "        import RS232_modified::*;"

    def ifacedecl(self):
        return "            interface RS232 uart{0}_coe;"


class twi(PBase):
    def importfn(self):
        return "        import I2C_top           :: *;"

    def ifacedecl(self):
        return "            interface I2C_out i2c{0}_out;" \
               "            method Bit#(1) i2c{0}_isint;"


class qspi(PBase):
    def importfn(self):
        return "        import qspi              :: *;"

    def ifacedecl(self):
        return "            interface QSPI_out qspi{0}_out;" \
               "            method Bit#(1) qspi{0}_isint;"


class pwm(PBase):
    def importfn(self):
        return "        import pwm::*;"

    def ifacedecl(self):
        return "        interface PWMIO pwm_o;"


class gpio(PBase):
    def importfn(self):
        return "     import pinmux::*;" \
               "     import mux::*;" \
               "     import gpio::*;"

    def ifacedecl(self):
        return "        interface GPIO_config#({1}) pad_config{0};"



class PFactory(object):
    def __init__(self):
        return {'uart': uart,
                'rs232': rs232,
                'twi': twi,
                'qspi', qspi,
                'pwm', pwm,
                'gpio', 'gpio'
                }
