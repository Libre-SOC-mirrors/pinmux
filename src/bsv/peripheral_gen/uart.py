from bsv.peripheral_gen.base import PBase


class uart(PBase):

    def slowimport(self):
        return "import Uart_bs         :: *;\n" + \
               "import RS232_modified::*;"

    def slowifdecl(self):
        return "interface RS232 uart{0}_coe;\n" + \
               "method Bit#(1) uart{0}_intr;"

    def num_axi_regs32(self):
        return 8

    def get_clock_reset(self, name, count):
        return "uart_clock,uart_reset"  

    def mkslow_peripheral(self, size=0):
        return "Ifc_Uart_bs uart{0} <- \n" + \
               "            mkUart_bs(clocked_by uart_clock,\n" + \
               "                    reset_by uart_reset, sp_clock, sp_reset);"

    def _mk_connection(self, name=None, count=0):
        return "uart{0}.slave_axi_uart"

    def pinname_out(self, pname):
        return {'tx': 'coe_rs232.sout'}.get(pname, '')

    def pinname_in(self, pname):
        return {'rx': 'coe_rs232.sin'}.get(pname, '')
