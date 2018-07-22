from bsv.peripheral_gen.base import PBase

class jtag(PBase):

    def axi_slave_name(self, name, ifacenum):
        return ''

    def axi_slave_idx(self, idx, name, ifacenum):
        return ('', 0)

    def axi_addr_map(self, name, ifacenum):
        return ''

    def slowifdeclmux(self):
        return "        method  Action jtag_ms (Bit#(1) in);\n" +  \
               "        method  Bit#(1) jtag_di;\n" + \
               "        method  Action jtag_do (Bit#(1) in);\n" + \
               "        method  Action jtag_ck (Bit#(1) in);"

    def slowifinstance(self):
        return jtag_method_template # bit of a lazy hack this...

jtag_method_template = """\
        method  Action jtag_ms (Bit#(1) in);
          pinmux.peripheral_side.jtag_ms(in);
        endmethod
        method  Bit#(1) jtag_di=pinmux.peripheral_side.jtag_di;
        method  Action jtag_do (Bit#(1) in);
          pinmux.peripheral_side.jtag_do(in);
        endmethod
        method  Action jtag_ck (Bit#(1) in);
          pinmux.peripheral_side.jtag_ck(in);
        endmethod
"""
