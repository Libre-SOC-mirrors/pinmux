from bsv.peripheral_gen.base import PBase


class quart(PBase):

    def slowimport(self):
        return "    import Uart16550         :: *;"

    def irq_name(self):
        return "quart{0}_intr"

    def slowifdecl(self):
        return "            interface RS232_PHY_Ifc quart{0}_coe;\n" + \
               "            method Bit#(1) %s;" % self.irq_name()

    def get_clock_reset(self, name, count):
        return "slow_clock,slow_reset" # XXX TODO: change to uart_clock/reset

    def num_axi_regs32(self):
        return 8

    def mkslow_peripheral(self, size=0):
        return "        // XXX XXX TODO: change to uart_clock/reset" + \
               "        Uart16550_AXI4_Lite_Ifc quart{0} <- \n" + \
               "                mkUart16550(clocked_by sp_clock,\n" + \
               "                    reset_by sp_reset, sp_clock, sp_reset);"

    def _mk_connection(self, name=None, count=0):
        return "quart{0}.slave_axi_uart"

    def pinname_out(self, pname):
        return {'tx': 'coe_rs232.stx_out',
                'rts': 'coe_rs232.rts_out',
                }.get(pname, '')

    def pinname_in(self, pname):
        return {'rx': 'coe_rs232.srx_in',
                'cts': 'coe_rs232.cts_in'
                }.get(pname, '')

    def __disabled_mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        ret.append("    rule con_%s%d_io_in;" % (name, count))
        ret.append("       {0}{1}.coe_rs232.modem_input(".format(name, count))
        for idx, pname in enumerate(['rx', 'cts']):
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s" % sname
            ret.append("            {0},".format(ps))
        ret.append("            1'b1,1'b0,1'b1")
        ret.append("        );")
        ret.append("    endrule")

        return '\n'.join(ret)

    def num_irqs(self):
        return 1

    def plic_object(self, pname, idx):
        return "{0}_interrupt.read".format(pname)

    def mk_plic(self, inum, irq_offs):
        name = self.get_iname(inum)
        ret = [uart_plic_template.format(name, irq_offs)]
        (ret2, irq_offs) = PBase.mk_plic(self, inum, irq_offs)
        ret.append(ret2)
        return ('\n'.join(ret), irq_offs)

    def mk_ext_ifacedef(self, iname, inum):
        name = self.get_iname(inum)
        return "        method {0}_intr = {0}.irq;".format(name)

    def slowifdeclmux(self, name, count):
        sname = self.peripheral.iname().format(count)
        return "        method Bit#(1) %s_intr;" % sname


uart_plic_template = """\
     // PLIC {0} synchronisation with irq {1}
     SyncBitIfc#(Bit#(1)) {0}_interrupt <-
                                mkSyncBitToCC(sp_clock, uart_reset);
     rule plic_synchronize_{0}_interrupt_{1};
         {0}_interrupt.send({0}.irq);
     endrule
"""
