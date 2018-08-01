from bsv.peripheral_gen.base import PBase


class eint(PBase):

    def slowimport(self):
        size = len(self.peripheral.pinspecs)
        return "`define NUM_EINTS %d" % size

    def mkslow_peripheral(self, size=0):
        size = len(self.peripheral.pinspecs)
        return "Wire#(Bit#(%d)) wr_interrupt <- mkWire();" % size

    def axi_slave_name(self, idx, name, ifacenum, typ=''):
        return ''

    def axi_slave_idx(self, idx, name, ifacenum, typ):
        return ('', 0)

    def axi_addr_map(self, name, ifacenum):
        return ''

    def ifname_tweak(self, pname, typ, txt):
        if typ != 'in':
            return txt
        print "ifnameweak", pname, typ, txt
        return "wr_interrupt[{0}] <= ".format(pname)

    def _mk_pincon(self, name, count, typ):
        assert typ == 'slow', 'TODO: mkConnection for fast'
        ret = [PBase._mk_pincon(self, name, count, typ)]
        size = len(self.peripheral.pinspecs)
        ret.append(eint_pincon_template.format(size))
        ret.append("rule con_%s%d_io_in;" % (name, count))
        ret.append("     wr_interrupt <= ({")
        for idx, p in enumerate(self.peripheral.pinspecs):
            pname = p['name']
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.eint.%s" % sname
            comma = '' if idx == size - 1 else ','
            ret.append("             {0}{1}".format(ps, comma))
        ret.append("     });")
        ret.append("endrule")

        return '\n'.join(ret)


eint_pincon_template = '''\
    // EINT is offset at end of other peripheral interrupts
`ifdef PLIC
    for(Integer i=0;i<{0};i=i+ 1)begin
      rule connect_int_to_plic(wr_interrupt[i]==1);
                ff_gateway_queue[i+`NUM_SLOW_IRQS].enq(1);
                plic.ifc_external_irq[i+`NUM_SLOW_IRQS].irq_frm_gateway(True);
      endrule
    end
`endif
'''
