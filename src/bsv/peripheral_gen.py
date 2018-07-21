import types
from copy import deepcopy


class PBase(object):
    def __init__(self, name):
        self.name = name

    def slowifdeclmux(self):
        return ''

    def slowimport(self):
        return ''

    def num_axi_regs32(self):
        return 0

    def slowifdecl(self):
        return ''

    def axibase(self, name, ifacenum):
        name = name.upper()
        return "%(name)s%(ifacenum)dBase" % locals()

    def axiend(self, name, ifacenum):
        name = name.upper()
        return "%(name)s%(ifacenum)dEnd" % locals()

    def axi_reg_def(self, start, name, ifacenum):
        name = name.upper()
        offs = self.num_axi_regs32() * 4 * 16
        if offs == 0:
            return ('', 0)
        end = start + offs - 1
        bname = self.axibase(name, ifacenum)
        bend = self.axiend(name, ifacenum)
        comment = "%d 32-bit regs" % self.num_axi_regs32()
        return ("    `define %(bname)s 'h%(start)08X\n"
                "    `define %(bend)s  'h%(end)08X // %(comment)s" % locals(),
                offs)

    def axi_slave_name(self, name, ifacenum):
        name = name.upper()
        return "{0}{1}_slave_num".format(name, ifacenum)

    def axi_slave_idx(self, idx, name, ifacenum):
        name = self.axi_slave_name(name, ifacenum)
        return ("typedef {0} {1};".format(idx, name), 1)

    def axi_addr_map(self, name, ifacenum):
        bname = self.axibase(name, ifacenum)
        bend = self.axiend(name, ifacenum)
        name = self.axi_slave_name(name, ifacenum)
        return """\
        if(addr>=`{0} && addr<=`{1})
            return tuple2(True,fromInteger(valueOf({2})));
        else""".format(bname, bend, name)

    def mk_pincon(self, name, count):
        # TODO: really should be using bsv.interface_decl.Interfaces
        # pin-naming rules.... logic here is hard-coded to duplicate
        # it (see Interface.__init__ outen)
        ret = []
        for p in self.peripheral.pinspecs:
            typ = p['type']
            pname = p['name']
            #n = "{0}{1}".format(self.name, self.mksuffix(name, count))
            n = name  # "{0}{1}".format(self.name, self.mksuffix(name, count))
            ret.append("    //%s %s" % (n, str(p)))
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s" % sname
            if typ == 'out' or typ == 'inout':
                ret.append("    rule con_%s%d_%s_out;" % (name, count, pname))
                fname = self.pinname_out(pname)
                if not n.startswith('gpio'): # XXX EURGH! horrible hack
                  n_ = "{0}{1}".format(n, count)
                else:
                  n_ = n
                if fname:
                    if p.get('outen'):
                        ps_ = ps + '_out'
                    else:
                        ps_ = ps
                    ret.append("      {0}({1}.{2});".format(ps_, n_, fname))
                fname = None
                if p.get('outen'):
                    fname = self.pinname_outen(pname)
                if fname:
                    if isinstance(fname, str):
                        fname = "{0}.{1}".format(n_, fname)
                    fname = self.pinname_tweak(pname, 'outen', fname)
                    ret.append("      {0}_outen({1});".format(ps, fname))
                ret.append("    endrule")
            if typ == 'in' or typ == 'inout':
                fname = self.pinname_in(pname)
                if fname:
                    if p.get('outen'):
                        ps_ = ps + '_in'
                    else:
                        ps_ = ps
                    ret.append(
                        "    rule con_%s%d_%s_in;" %
                        (name, count, pname))
                    n_ = "{0}{1}".format(n, count)
                    ret.append("      {1}.{2}({0});".format(ps_, n_, fname))
                    ret.append("    endrule")
        return '\n'.join(ret)

    def mk_cellconn(self, *args):
        return ''

    def mkslow_peripheral(self, size=0):
        return ''

    def mksuffix(self, name, i):
        return i

    def __mk_connection(self, con, aname):
        txt = "        mkConnection (slow_fabric.v_to_slaves\n" + \
            "                    [fromInteger(valueOf({1}))],\n" + \
            "                    {0});"

        print "PBase __mk_connection", self.name, aname
        if not con:
            return ''
        return txt.format(con, aname)

    def mk_connection(self, count, name=None):
        if name is None:
            name = self.name
        print "PBase mk_conn", self.name, count
        aname = self.axi_slave_name(name, count)
        #dname = self.mksuffix(name, count)
        #dname = "{0}{1}".format(name, dname)
        con = self._mk_connection(name, count).format(count, aname)
        return self.__mk_connection(con, aname)

    def _mk_connection(self, name=None, count=0):
        return ''

    def pinname_out(self, pname):
        return ''

    def pinname_in(self, pname):
        return ''

    def pinname_outen(self, pname):
        return ''

    def pinname_tweak(self, pname, typ, txt):
        return txt


class uart(PBase):

    def slowimport(self):
        return "          import Uart_bs         :: *;\n" + \
               "          import RS232_modified::*;"

    def slowifdecl(self):
        return "            interface RS232 uart{0}_coe;\n" + \
               "            method Bit#(1) uart{0}_intr;"

    def num_axi_regs32(self):
        return 8

    def mkslow_peripheral(self, size=0):
        return "        Ifc_Uart_bs uart{0} <- \n" + \
               "                mkUart_bs(clocked_by sp_clock,\n" + \
               "                    reset_by uart_reset, sp_clock, sp_reset);"

    def _mk_connection(self, name=None, count=0):
        return "uart{0}.slave_axi_uart"

    def pinname_out(self, pname):
        return {'tx': 'coe_rs232.sout'}.get(pname, '')

    def pinname_in(self, pname):
        return {'rx': 'coe_rs232.sin'}.get(pname, '')


class qquart(PBase):

    def slowimport(self):
        return "          import Uart16550         :: *;"

    def slowifdecl(self):
        return "            interface RS232_PHY_Ifc uart{0}_coe;\n" + \
               "            method Bit#(1) uart{0}_intr;"

    def num_axi_regs32(self):
        return 8

    def mkslow_peripheral(self, size=0):
        return "        Uart16550_AXI4_Lite_Ifc uart{0} <- \n" + \
               "                mkUart16550(clocked_by sp_clock,\n" + \
               "                    reset_by uart_reset, sp_clock, sp_reset);"

    def _mk_connection(self, name=None, count=0):
        return "uart{0}.slave_axi_uart"

    def pinname_out(self, pname):
        return {'tx': 'coe_rs232.sout'}.get(pname, '')

    def pinname_in(self, pname):
        return {'rx': 'coe_rs232.sin'}.get(pname, '')


class rs232(PBase):

    def slowimport(self):
        return "        import Uart_bs::*;\n" + \
               "        import RS232_modified::*;"

    def slowifdecl(self):
        return "            interface RS232 uart{0}_coe;"

    def num_axi_regs32(self):
        return 2

    def mkslow_peripheral(self, size=0):
        return "        //Ifc_Uart_bs uart{0} <-" + \
               "        //       mkUart_bs(clocked_by uart_clock,\n" + \
               "        //          reset_by uart_reset,sp_clock, sp_reset);" +\
               "        Ifc_Uart_bs uart{0} <-" + \
               "                mkUart_bs(clocked_by sp_clock,\n" + \
               "                    reset_by sp_reset, sp_clock, sp_reset);"

    def _mk_connection(self, name=None, count=0):
        return "uart{0}.slave_axi_uart"

    def pinname_out(self, pname):
        return {'tx': 'coe_rs232.sout'}.get(pname, '')

    def pinname_in(self, pname):
        return {'rx': 'coe_rs232.sin'}.get(pname, '')


class twi(PBase):

    def slowimport(self):
        return "        import I2C_top           :: *;"

    def slowifdecl(self):
        return "            interface I2C_out twi{0}_out;\n" + \
               "            method Bit#(1) twi{0}_isint;"

    def num_axi_regs32(self):
        return 8

    def mkslow_peripheral(self, size=0):
        return "        I2C_IFC twi{0} <- mkI2CController();"

    def _mk_connection(self, name=None, count=0):
        return "twi{0}.slave_i2c_axi"

    def pinname_out(self, pname):
        return {'sda': 'out.sda_out',
                'scl': 'out.scl_out'}.get(pname, '')

    def pinname_in(self, pname):
        return {'sda': 'out.sda_in',
                'scl': 'out.scl_in'}.get(pname, '')

    def pinname_outen(self, pname):
        return {'sda': 'out.sda_out_en',
                'scl': 'out.scl_out_en'}.get(pname, '')

    def pinname_tweak(self, pname, typ, txt):
        if typ == 'outen':
            return "pack({0})".format(txt)
        return txt


class eint(PBase):

    def mkslow_peripheral(self, size=0):
        size = len(self.peripheral.pinspecs)
        return "        Wire#(Bit#(%d)) wr_interrupt <- mkWire();" % size


    def axi_slave_name(self, name, ifacenum):
        return ''

    def axi_slave_idx(self, idx, name, ifacenum):
        return ('', 0)

    def axi_addr_map(self, name, ifacenum):
        return ''

    def _pinname_out(self, pname):
        return {'sda': 'out.sda_out',
                'scl': 'out.scl_out'}.get(pname, '')

    def _pinname_in(self, pname):
        return {'sda': 'out.sda_in',
                'scl': 'out.scl_in'}.get(pname, '')

    def _pinname_outen(self, pname):
        return {'sda': 'out.sda_out_en',
                'scl': 'out.scl_out_en'}.get(pname, '')

    def mk_pincon(self, name, count):
        size = len(self.peripheral.pinspecs)
        ret = []
        ret.append(eint_pincon_template.format(size))

        ret.append("    rule con_%s%d_io_out;" % (name, count))
        for idx, p in enumerate(self.peripheral.pinspecs):
            pname = p['name']
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s_out" % sname
            ret.append("        wr_interript[{0}] <= {1};".format(idx, ps))
        for idx, p in enumerate(self.peripheral.pinspecs):
            pname = p['name']
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s_out_en" % sname
            ret.append("        {0} <= 1'b1;".format(ps))
        ret.append("    endrule")
        return '\n'.join(ret)


eint_pincon_template = '''\
    // TODO: offset i by the number of eints already used
    for(Integer i=0;i<{0};i=i+ 1)begin
      rule connect_int_to_plic(wr_interrupt[i]==1);
                ff_gateway_queue[i].enq(1);
                plic.ifc_external_irq[i].irq_frm_gateway(True);
      endrule
    end
'''


class spi(PBase):

    def slowimport(self):
        return "        import qspi              :: *;"

    def slowifdecl(self):
        return "            interface QSPI_out spi{0}_out;\n" + \
               "            method Bit#(1) spi{0}_isint;"

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self):
        return "        Ifc_qspi spi{0} <-  mkqspi();"

    def _mk_connection(self, name=None, count=0):
        return "spi{0}.slave"

    def pinname_out(self, pname):
        return {'clk': 'out.clk_o',
                'nss': 'out.ncs_o',
                'mosi': 'out.io_o[0]',
                'miso': 'out.io_o[1]',
                }.get(pname, '')

    def pinname_outen(self, pname):
        return {'clk': 1,
                'nss': 1,
                'mosi': 'out.io_enable[0]',
                'miso': 'out.io_enable[1]',
                }.get(pname, '')

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        plen = len(self.peripheral.pinspecs)
        ret.append("    // XXX NSS and CLK are hard-coded master")
        ret.append("    // TODO: must add spi slave-mode")
        ret.append("    // all ins done in one rule from 4-bitfield")
        ret.append("    rule con_%s%d_io_in;" % (name, count))
        ret.append("       {0}{1}.out.io_i({{".format(name, count))
        for idx, pname in enumerate(['mosi', 'miso']):
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s_in" % sname
            ret.append("            {0},".format(ps))
        ret.append("            1'b0,1'b0")
        ret.append("        });")
        ret.append("    endrule")
        return '\n'.join(ret)


class qspi(PBase):

    def slowimport(self):
        return "        import qspi              :: *;"

    def slowifdecl(self):
        return "            interface QSPI_out qspi{0}_out;\n" + \
               "            method Bit#(1) qspi{0}_isint;"

    def num_axi_regs32(self):
        return 13

    def mkslow_peripheral(self, size=0):
        return "        Ifc_qspi qspi{0} <-  mkqspi();"

    def _mk_connection(self, name=None, count=0):
        return "qspi{0}.slave"

    def pinname_out(self, pname):
        return {'ck': 'out.clk_o',
                'nss': 'out.ncs_o',
                'io0': 'out.io_o[0]',
                'io1': 'out.io_o[1]',
                'io2': 'out.io_o[2]',
                'io3': 'out.io_o[3]',
                }.get(pname, '')

    def pinname_outen(self, pname):
        return {'ck': 1,
                'nss': 1,
                'io0': 'out.io_enable[0]',
                'io1': 'out.io_enable[1]',
                'io2': 'out.io_enable[2]',
                'io3': 'out.io_enable[3]',
                }.get(pname, '')

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        plen = len(self.peripheral.pinspecs)
        ret.append("    // XXX NSS and CLK are hard-coded master")
        ret.append("    // TODO: must add qspi slave-mode")
        ret.append("    // all ins done in one rule from 4-bitfield")
        ret.append("    rule con_%s%d_io_in;" % (name, count))
        ret.append("       {0}{1}.out.io_i({{".format(name, count))
        for i, p in enumerate(self.peripheral.pinspecs):
            typ = p['type']
            pname = p['name']
            if not pname.startswith('io'):
                continue
            idx = pname[1:]
            n = name
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s_in" % sname
            comma = '' if i == 5 else ','
            ret.append("            {0}{1}".format(ps, comma))
        ret.append("        });")
        ret.append("    endrule")
        return '\n'.join(ret)


class pwm(PBase):

    def slowimport(self):
        return "        import pwm::*;"

    def slowifdecl(self):
        return "        interface PWMIO pwm{0}_io;"

    def num_axi_regs32(self):
        return 4

    def mkslow_peripheral(self, size=0):
        return "        Ifc_PWM_bus pwm{0} <- mkPWM_bus(sp_clock);"

    def _mk_connection(self, name=None, count=0):
        return "pwm{0}.axi4_slave"

    def pinname_out(self, pname):
        return {'out': 'pwm_io.pwm_o'}.get(pname, '')


class gpio(PBase):

    def slowimport(self):
        return "     import pinmux::*;\n" + \
               "     import mux::*;\n" + \
               "     import gpio::*;\n"

    def slowifdeclmux(self):
        size = len(self.peripheral.pinspecs)
        return "    interface GPIO_config#(%d) pad_config{0};" % size

    def num_axi_regs32(self):
        return 2

    def axi_slave_idx(self, idx, name, ifacenum):
        """ generates AXI slave number definition, except
            GPIO also has a muxer per bank
        """
        name = name.upper()
        mname = 'mux' + name[4:]
        mname = mname.upper()
        print "AXIslavenum", name,  mname
        (ret, x) = PBase.axi_slave_idx(self, idx, name, ifacenum)
        (ret2, x) = PBase.axi_slave_idx(self, idx+1, mname, ifacenum)
        return ("%s\n%s" % (ret, ret2), 2)

    def mkslow_peripheral(self, size=0):
        print "gpioslow", self.peripheral,  dir(self.peripheral)
        size = len(self.peripheral.pinspecs)
        return "        MUX#(%d) mux{0} <- mkmux();\n" % size + \
               "        GPIO#(%d) gpio{0} <- mkgpio();" % size

    def mk_connection(self, count):
        print "GPIO mk_conn", self.name, count
        res = []
        dname = self.mksuffix(self.name, count)
        for i, n in enumerate(['gpio' + dname, 'mux' + dname]):
            res.append(PBase.mk_connection(self, count, n))
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
        txt = "       pinmux.mux_lines.cell{0}_mux(mux{1}.mux_config.mux[{2}]);"
        for p in self.peripheral.pinspecs:
            ret.append(txt.format(cellnum, bank, p['name'][1:]))
            cellnum += 1
        return ("\n".join(ret), cellnum)

    def pinname_out(self, pname):
        return "func.gpio_out[{0}]".format(pname[1:])

    def pinname_outen(self, pname):
        return "func.gpio_out_en[{0}]".format(pname[1:])

    def mk_pincon(self, name, count):
        ret = [PBase.mk_pincon(self, name, count)]
        # special-case for gpio in, store in a temporary vector
        plen = len(self.peripheral.pinspecs)
        ret.append("    rule con_%s%d_in;" % (name, count))
        ret.append("       Vector#({0},Bit#(1)) temp;".format(plen))
        for p in self.peripheral.pinspecs:
            typ = p['type']
            pname = p['name']
            idx = pname[1:]
            n = name
            sname = self.peripheral.pname(pname).format(count)
            ps = "pinmux.peripheral_side.%s_in" % sname
            ret.append("        temp[{0}]={1};".format(idx, ps))
        ret.append("        {0}.func.gpio_in(temp);".format(name))
        ret.append("    endrule")
        return '\n'.join(ret)


axi_slave_declarations = """\
typedef  0  SlowMaster;
{0}
typedef  TAdd#(LastGen_slave_num,`ifdef CLINT       1 `else 0 `endif )
              CLINT_slave_num;
typedef  TAdd#(CLINT_slave_num  ,`ifdef PLIC        1 `else 0 `endif )
              Plic_slave_num;
typedef  TAdd#(Plic_slave_num   ,`ifdef AXIEXP      1 `else 0 `endif )
              AxiExp1_slave_num;
typedef TAdd#(AxiExp1_slave_num,1) Num_Slow_Slaves;
"""

pinmux_cellrule = """\
    rule connect_select_lines_pinmux;
{0}
    endrule
"""


class CallFn(object):
    def __init__(self, peripheral, name):
        self.peripheral = peripheral
        self.name = name

    def __call__(self, *args):
        #print "__call__", self.name, self.peripheral.slow, args
        if not self.peripheral.slow:
            return ''
        return getattr(self.peripheral.slow, self.name)(*args[1:])


class PeripheralIface(object):
    def __init__(self, ifacename):
        self.slow = None
        slow = slowfactory.getcls(ifacename)
        print "Iface", ifacename, slow
        if slow:
            self.slow = slow(ifacename)
            self.slow.peripheral = self
        for fname in ['slowimport', 'slowifdecl', 'slowifdeclmux', 
                      'mkslow_peripheral',
                      'mk_connection', 'mk_cellconn', 'mk_pincon']:
            fn = CallFn(self, fname)
            setattr(self, fname, types.MethodType(fn, self))

        #print "PeripheralIface"
        #print dir(self)

    def mksuffix(self, name, i):
        if self.slow is None:
            return i
        return self.slow.mksuffix(name, i)

    def axi_reg_def(self, start, count):
        if not self.slow:
            return ('', 0)
        return self.slow.axi_reg_def(start, self.ifacename, count)

    def axi_slave_idx(self, start, count):
        if not self.slow:
            return ('', 0)
        return self.slow.axi_slave_idx(start, self.ifacename, count)

    def axi_addr_map(self, count):
        if not self.slow:
            return ''
        return self.slow.axi_addr_map(self.ifacename, count)


class PeripheralInterfaces(object):
    def __init__(self):
        pass

    def slowimport(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            #print "slowimport", name, self.data[name].slowimport
            ret.append(self.data[name].slowimport())
        return '\n'.join(list(filter(None, ret)))

    def slowifdeclmux(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                ret.append(self.data[name].slowifdeclmux().format(i, name))
        return '\n'.join(list(filter(None, ret)))

    def slowifdecl(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                ret.append(self.data[name].slowifdecl().format(i, name))
        return '\n'.join(list(filter(None, ret)))

    def axi_reg_def(self, *args):
        ret = []
        start = 0x00011100  # start of AXI peripherals address
        for (name, count) in self.ifacecount:
            for i in range(count):
                x = self.data[name].axi_reg_def(start, i)
                #print ("ifc", name, x)
                (rdef, offs) = x
                ret.append(rdef)
                start += offs
        return '\n'.join(list(filter(None, ret)))

    def axi_slave_idx(self, *args):
        ret = []
        start = 0
        for (name, count) in self.ifacecount:
            for i in range(count):
                (rdef, offs) = self.data[name].axi_slave_idx(start, i)
                #print ("ifc", name, rdef, offs)
                ret.append(rdef)
                start += offs
        ret.append("typedef %d LastGen_slave_num;" % (start - 1))
        decls = '\n'.join(list(filter(None, ret)))
        return axi_slave_declarations.format(decls)

    def axi_addr_map(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                ret.append(self.data[name].axi_addr_map(i))
        return '\n'.join(list(filter(None, ret)))

    def mkslow_peripheral(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                print "mkslow", name, count
                x = self.data[name].mkslow_peripheral()
                print name, count, x
                suffix = self.data[name].mksuffix(name, i)
                ret.append(x.format(suffix))
        return '\n'.join(list(filter(None, ret)))

    def mk_connection(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                print "mk_conn", name, i
                txt = self.data[name].mk_connection(i)
                if name == 'gpioa':
                    print "txt", txt
                    print self.data[name].mk_connection
                ret.append(txt)
        return '\n'.join(list(filter(None, ret)))

    def mk_cellconn(self):
        ret = []
        cellcount = 0
        for (name, count) in self.ifacecount:
            for i in range(count):
                res = self.data[name].mk_cellconn(cellcount, name, i)
                if not res:
                    continue
                (txt, cellcount) = res
                ret.append(txt)
        ret = '\n'.join(list(filter(None, ret)))
        return pinmux_cellrule.format(ret)

    def mk_pincon(self):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                txt = self.data[name].mk_pincon(name, i)
                ret.append(txt)
        return '\n'.join(list(filter(None, ret)))


class PFactory(object):
    def getcls(self, name):
        for k, v in {'uart': uart,
                     'rs232': rs232,
                     'twi': twi,
                     'qspi': qspi,
                     'spi': spi,
                     'pwm': pwm,
                     'eint': eint,
                     'gpio': gpio
                     }.items():
            if name.startswith(k):
                return v
        return None


slowfactory = PFactory()

if __name__ == '__main__':
    p = uart('uart')
    print p.slowimport()
    print p.slowifdecl()
    i = PeripheralIface('uart')
    print i, i.slow
    i = PeripheralIface('gpioa')
    print i, i.slow
