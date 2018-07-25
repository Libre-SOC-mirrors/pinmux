from bsv.peripheral_gen.base import PBase


class jtag(PBase):

    def slowimport(self):
        return "    import jtagtdm::*;\n"

    def fastifdecl(self, name, count):
        # YUK!
        template = """ \
         (*always_ready,always_enabled*) method Action tms_i(Bit#(1) tms);
         (*always_ready,always_enabled*) method Action tdi_i(Bit#(1) tdi);
         (*always_ready,always_enabled*)
                                 method Action bs_chain_i(Bit#(1) bs_chain);
         (*always_ready,always_enabled*) method Bit#(1) shiftBscan2Edge;
         (*always_ready,always_enabled*) method Bit#(1) selectJtagInput;
         (*always_ready,always_enabled*) method Bit#(1) selectJtagOutput;
         (*always_ready,always_enabled*) method Bit#(1) updateBscan;
         (*always_ready,always_enabled*) method Bit#(1) bscan_in;
         (*always_ready,always_enabled*) method Bit#(1) scan_shift_en;
         (*always_ready,always_enabled*) method Bit#(1) tdo;
         (*always_ready,always_enabled*) method Bit#(1) tdo_oe;
"""
        return template

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
    def axi_slave_name(self, name, ifacenum, typ=''):
        return ''

    def axi_slave_idx(self, idx, name, ifacenum, typ):
        return ('', 0)

    def axi_addr_map(self, name, ifacenum):
        return ''
