from bsv.peripheral_gen.base import PBase


class jtag(PBase):

    def slowimport(self):
        return "import jtagdtm::*;\n"

    def extfastifinstance(self, name, count):
        return self._extifinstance(name, count, "_out", "", True)

    def fastifdecl(self, name, count):
        # YUK!
        return "interface Ifc_jtagdtm jtag{0}_out;".format(count)

    def get_clock_reset(self, name, count):
        return "tck, trst"

    def pinname_in(self, pname):
        return {'tms': 'tms',
                'tdi': 'tdi',
                }.get(pname, '')

    def pinname_out(self, pname):
        return {'tck': 'tck',
                'tdo': 'tdo',
                }.get(pname, '')

    def mkfast_peripheral(self):
        return """\
Ifc_jtagdtm jtag{0} <-mkjtagdtm(clocked_by tck, reset_by trst);
rule drive_tmp_scan_outs;
    jtag{0}.scan_out_1_i(1'b0);
    jtag{0}.scan_out_2_i(1'b0);
    jtag{0}.scan_out_3_i(1'b0);
    jtag{0}.scan_out_4_i(1'b0);
    jtag{0}.scan_out_5_i(1'b0);
endrule
"""

    def axi_slave_name(self, name, ifacenum, typ=None):
        return ''

    def axi_slave_idx(self, idx, name, ifacenum, typ):
        return ('', 0)

    def axi_addr_map(self, name, ifacenum, typ=None):
        return ''
