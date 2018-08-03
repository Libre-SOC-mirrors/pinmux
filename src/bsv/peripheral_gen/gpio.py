from bsv.peripheral_gen.base import PBase


class gpio(PBase):

    def slowimport(self):
        return "import pinmux::*;\n" + \
               "import mux::*;\n" + \
               "import gpio::*;\n"

    def extifinstance2(self, name, count):
        template = "interface pad_config{0} = {1}.pad_config;"
        dname = self.mksuffix(self.name, count)
        return template.format(dname, name)

    def slowifdeclmux(self, name, count):
        size = len(self.peripheral.pinspecs)
        dname = self.mksuffix(self.name, count)
        return "interface GPIO_config#(%d) pad_config%s;" % \
            (size, dname)

    def num_axi_regs32(self):
        return 2

    def axi_slave_idx(self, idx, name, ifacenum, typ):
        """ generates AXI slave number definition, except
            GPIO also has a muxer per bank
        """
        name = name.upper()
        mname = 'mux' + name[4:]
        mname = mname.upper()
        print "AXIslavenum", name, mname
        (ret, x) = PBase.axi_slave_idx(self, idx, name, ifacenum, typ)
        (ret2, x) = PBase.axi_slave_idx(self, idx + 1, mname, ifacenum, typ)
        return ("%s\n%s" % (ret, ret2), 2)

    def mkslow_peripheral(self, size=0):
        print "gpioslow", self.peripheral, dir(self.peripheral)
        size = len(self.peripheral.pinspecs)
        dflt = "%s" % ("0"*size*2) # XX TODO: read default from config
        return "MUX#(%d) mux{0} <- mkmux(`b%s);\n" % (size, dflt)+ \
               "GPIO#(%d) gpio{0} <- mkgpio();" % size

    def mk_connection(self, count, fabricname, typ):
        print "GPIO mk_conn", self.name, count
        res = []
        dname = self.mksuffix(self.name, count)
        for i, n in enumerate(['gpio' + dname, 'mux' + dname]):
            res.append(PBase.mk_connection(self, count, fabricname, typ, n))
        return '\n'.join(res)

    def _mk_connection(self, name=None, count=0):
        n = self.mksuffix(name, count)
        if name.startswith('gpio'):
            return "gpio{0}.axi_slave".format(n)
        if name.startswith('mux'):
            return "mux{0}.axi_slave".format(n)

    def mksuffix(self, name, i):
        if name.startswith('mux'):
            return name[3:]
        return name[4:]

    def mk_cellconn(self, cellnum, name, count):
        ret = []
        bank = self.mksuffix(name, count)
        txt = "pinmux.mux_lines.cell{0}_mux(mux{1}.mux_config.mux[{2}]);"
        for p in self.peripheral.pinspecs:
            ret.append(txt.format(cellnum, bank, p['name'][1:]))
            cellnum += 1
        return ("\n".join(ret), cellnum)

    def pinname_out(self, pname):
        return "func.gpio_out[{0}]".format(pname[1:])

    def pinname_outen(self, pname):
        return "func.gpio_out_en[{0}]".format(pname[1:])

    def _mk_pincon(self, name, count, typ):
        #ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        assert typ == 'slow'
        ret = []
        plen = len(self.peripheral.pinspecs)
        template = "mkConnection({0}.{1},\n\t\t\t{2}_{1});"
        ps = "pinmux.peripheral_side.%s" % name
        n = "{0}.func.gpio".format(name)
        for ptype in ['out', 'out_en', 'in']:
            ret.append(template.format(ps, ptype, n))
        return '\n'.join(ret)
