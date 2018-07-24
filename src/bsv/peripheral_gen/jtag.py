from bsv.peripheral_gen.base import PBase


class jtag(PBase):

    def axi_slave_name(self, name, ifacenum):
        return ''

    def axi_slave_idx(self, idx, name, ifacenum):
        return ('', 0)

    def axi_addr_map(self, name, ifacenum):
        return ''

    def slowifdeclmux(self, name, count):
        sname = self.get_iname(count)
        return "        interface PeripheralSideJTAG %s;" % sname

    def slowifinstance(self, name, count):
        sname = self.peripheral.iname().format(count)
        pname = self.get_iname(count)
        template = "        interface {0} = pinmux.peripheral_side.{1};"
        return template.format(pname, sname)

