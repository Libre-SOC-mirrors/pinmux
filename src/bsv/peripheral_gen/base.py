import types

def li(txt, indent):
    indent = ' ' * indent
    istxt = False
    if isinstance(txt, str):
        istxt = True
        txt = txt.split('\n')
    res = []
    for line in txt:
        line = line.split('\n')
        res += line
    txt = res
    res = []
    for line in txt:
        res.append(indent + line)
    if istxt:
        res = '\n'.join(res)
    return res


class PBase(object):
    def __init__(self, name):
        self.name = name

    def extifdecl(self, name, count):
        sname = self.get_iname(count)
        return "interface PeripheralSide%s %s;" % (name.upper(), sname)

    def has_axi_master(self):
        return False

    def irq_name(self):
        return ""

    def mk_dma_irq(self, name, count):
        if not self.irq_name():
            return ''
        sname = self.get_iname(count)
        return "{0}_interrupt".format(sname)

    def mk_dma_rule(self, name, count):
        irqname = self.mk_dma_irq(name, count)
        if not irqname:
            return ''
        pirqname = self.irq_name().format(count)
        template = "   {0}_interrupt.send(\n" + \
                   "           slow_peripherals.{1});"
        return template.format(irqname, pirqname)

    def get_clock_reset(self, name, count):
        return "slow_clock,slow_reset"

    def mk_dma_sync(self, name, count):
        irqname = self.mk_dma_irq(name, count)
        if not irqname:
            return ''
        sname = self.peripheral.iname().format(count)
        template = "SyncBitIfc#(Bit#(1)) {0} <-\n" + \
                   "           <-mkSyncBitToCC({1});"
        return template.format(irqname, self.get_clock_reset(name, count))

    def mk_dma_connect(self, name, count):
        irqname = self.mk_dma_irq(name, count)
        if not irqname:
            return ''
        return "{0}.read".format(irqname)

    def fastifdecl(self, name, count):
        return ''

    def slowifdeclmux(self, name, count):
        return ''

    def slowimport(self):
        return ''

    def num_axi_regs32(self):
        return 0

    def slowifdecl(self):
        return ''

    def get_iname(self, inum):
        return "{0}{1}".format(self.name, self.mksuffix(self.name, inum))

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

    def axi_master_name(self, name, ifacenum, typ=''):
        name = name.upper()
        return "{0}{1}_master_num".format(name, ifacenum)

    def axi_slave_name(self, name, ifacenum, typ=''):
        name = name.upper()
        return "{0}{1}_{2}slave_num".format(name, ifacenum, typ)

    def axi_master_idx(self, idx, name, ifacenum, typ):
        name = self.axi_master_name(name, ifacenum, typ)
        return ("typedef {0} {1};".format(idx, name), 1)

    def axi_slave_idx(self, idx, name, ifacenum, typ):
        name = self.axi_slave_name(name, ifacenum, typ)
        return ("typedef {0} {1};".format(idx, name), 1)

    def axi_addr_map(self, name, ifacenum):
        bname = self.axibase(name, ifacenum)
        bend = self.axiend(name, ifacenum)
        name = self.axi_slave_name(name, ifacenum)
        template = """\
if(addr>=`{0} && addr<=`{1})
    return tuple2(True,fromInteger(valueOf({2})));
else"""
        return template.format(bname, bend, name)

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
            ret.append("//%s %s" % (n, str(p)))
            sname = self.peripheral.iname().format(count)
            sname = "{0}.{1}".format(sname, pname)
            ps = "pinmux.peripheral_side.%s" % sname
            if typ == 'out' or typ == 'inout':
                fname = self.pinname_out(pname)
                if not n.startswith('gpio'):  # XXX EURGH! horrible hack
                    n_ = "{0}{1}".format(n, count)
                else:
                    n_ = n
                if fname:
                    if p.get('outen'):
                        ps_ = ps + '_out'
                    else:
                        ps_ = ps
                    ret.append("mkConnection({0},\n\t\t\t{1}.{2});"
                               .format(ps_, n_, fname))
                fname = None
                if p.get('outen'):
                    fname = self.pinname_outen(pname)
                if fname:
                    if isinstance(fname, str):
                        fname = "{0}.{1}".format(n_, fname)
                    fname = self.pinname_tweak(pname, 'outen', fname)
                    ret.append("mkConnection({0}_outen,\n\t\t\t{1});"
                               .format(ps, fname))
            if typ == 'in' or typ == 'inout':
                fname = self.pinname_in(pname)
                if fname:
                    if p.get('outen'):
                        ps_ = ps + '_in'
                    else:
                        ps_ = ps
                    n_ = "{0}{1}".format(n, count)
                    n_ = '{0}.{1}'.format(n_, fname)
                    n_ = self.ifname_tweak(pname, 'in', n_)
                    ret.append("mkConnection({1}, {0});".format(ps_, n_))
        return '\n'.join(ret)

    def mk_cellconn(self, *args):
        return ''

    def mkfast_peripheral(self, size=0):
        return ''

    def mkslow_peripheral(self, size=0):
        return ''

    def mksuffix(self, name, i):
        return i

    def __mk_connection(self, con, aname, fabricname):
        txt = "mkConnection ({2}.v_to_slaves\n" + \
              "            [fromInteger(valueOf({1}))],\n" + \
              "            {0});"

        print "PBase __mk_connection", self.name, aname
        if not con:
            return ''
        return txt.format(con, aname, fabricname)

    def __mk_master_connection(self, con, aname):
        txt = "mkConnection (slow_fabric.v_to_slaves\n" + \
              "            [fromInteger(valueOf({1}))],\n" + \
              "            {0});"

        print "PBase __mk_connection", self.name, aname
        if not con:
            return ''
        return txt.format(con, aname)

    def mk_connection(self, count, fabricname, typ, name=None):
        if name is None:
            name = self.name
        print "PBase mk_conn", self.name, count
        aname = self.axi_slave_name(name, count, typ)
        #dname = self.mksuffix(name, count)
        #dname = "{0}{1}".format(name, dname)
        con = self._mk_connection(name, count).format(count, aname)
        return self.__mk_connection(con, aname, fabricname)

    def _mk_connection(self, name=None, count=0):
        return ''

    def pinname_out(self, pname):
        return ''

    def pinname_in(self, pname):
        return ''

    def pinname_outen(self, pname):
        return ''

    def ifname_tweak(self, pname, typ, txt):
        return txt

    def pinname_tweak(self, pname, typ, txt):
        return txt

    def num_irqs(self):
        return 0

    def mk_plic(self, inum, irq_offs):
        res = []
        print "mk_plic", self.name, inum, irq_offs
        niq = self.num_irqs()
        if niq == 0:
            return ('', irq_offs)
        name = self.get_iname(inum)
        res.append("// PLIC rules for {0}".format(name))
        for idx in range(niq):
            plic_obj = self.plic_object(name, idx)
            print "plic_obj", name, idx, plic_obj
            plic = mkplic_rule.format(name, plic_obj, irq_offs)
            res.append(plic)
            irq_offs += 1  # increment to next irq
        return ('\n'.join(res), irq_offs)

    def mk_ext_ifacedef(self, iname, inum):
        return ''

    def extfastifinstance(self, name, count):
        return ''

    def _extifinstance(self, name, count, suffix, prefix, samename=False):
        pname = self.get_iname(count)
        if samename:
            sname = pname
        else:
            sname = self.peripheral.iname().format(count)
        template = "interface {0}{3} = {2}{1};"
        return template.format(pname, sname, prefix, suffix)

    def extifinstance2(self, name, count):
        return ''

    def extifinstance(self, name, count):
        return self._extifinstance(name, count, "",
                                            "pinmux.peripheral_side.")


mkplic_rule = """\
rule rl_connect_{0}_to_plic_{2};
   if({1} == 1'b1) begin
       ff_gateway_queue[{2}].enq(1);
       plic.ifc_external_irq[{2}].irq_frm_gateway(True);
   end
endrule
"""

axi_master_declarations= """\
typedef 0 Dmem_master_num;
typedef 1 Imem_master_num;
{0}
typedef TAdd#(LastGen_master_num, `ifdef Debug 1 `else 0 `endif )
                Debug_master_num;
typedef TAdd#(Debug_master_num, `ifdef DMA 1 `else 0 `endif )
                DMA_master_num;
typedef TAdd#(DMA_master_num,1)
                Num_Masters;
"""

axi_fastslave_declarations = """\
{0}
typedef  TAdd#(LastGen_fastslave_num,1)      Sdram_cfg_slave_num;
typedef  TAdd#(Sdram_slave_num   ,`ifdef SDRAM      1 `else 0 `endif )
                      Sdram_cfg_slave_num;
typedef TAdd#(Sdram_cfg_slave_num,`ifdef BOOTROM    1 `else 0 `endif )
                BootRom_slave_num   ;
typedef TAdd#(BootRom_slave_num  ,`ifdef Debug      1 `else 0 `endif )
                Debug_slave_num ;
typedef  TAdd#(Debug_slave_num   , `ifdef TCMemory  1 `else 0 `endif )
                TCM_slave_num;
typedef  TAdd#(TCM_slave_num     ,`ifdef DMA            1 `else 0 `endif )
                Dma_slave_num;
typedef  TAdd#(Dma_slave_num      ,1 )      SlowPeripheral_slave_num;
typedef  TAdd#(SlowPeripheral_slave_num,`ifdef VME  1 `else 0 `endif )
                VME_slave_num;
typedef  TAdd#(VME_slave_num,`ifdef FlexBus 1 `else 0 `endif )
                FlexBus_slave_num;
typedef TAdd#(FlexBus_slave_num,1)
                Num_Slaves;

"""

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
        for fname in ['slowimport',
                      'extfastifinstance',
                      'extifinstance2', 'extifinstance', 'extifdecl',
                      'slowifdecl', 'slowifdeclmux',
                      'fastifdecl',
                      'mkslow_peripheral',
                      'mk_dma_sync', 'mk_dma_connect', 'mk_dma_rule',
                      'mkfast_peripheral',
                      'mk_plic', 'mk_ext_ifacedef',
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

    def axi_master_idx(self, start, count, typ):
        if not self.slow or not self.slow.has_axi_master():
            return ('', 0)
        return self.slow.axi_master_idx(start, self.ifacename, count, typ)

    def axi_slave_idx(self, start, count, typ):
        if not self.slow:
            return ('', 0)
        return self.slow.axi_slave_idx(start, self.ifacename, count, typ)

    def axi_addr_map(self, count):
        if not self.slow:
            return ''
        return self.slow.axi_addr_map(self.ifacename, count)


class PeripheralInterfaces(object):
    def __init__(self):
        self.fastbusmode = False

    def slowimport(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            #print "slowimport", name, self.data[name].slowimport
            ret.append(self.data[name].slowimport())
        return '\n'.join(li(list(filter(None, ret)), 4))

    def extfastifinstance(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                iname = self.data[name].iname().format(i)
                print "extfast", iname, self.is_on_fastbus(name, i)
                if self.is_on_fastbus(name, i):
                    continue
                ret.append(self.data[name].extfastifinstance(name, i))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def extifinstance2(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                iname = self.data[name].iname().format(i)
                ret.append(self.data[name].extifinstance2(name, i))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def extifinstance(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                iname = self.data[name].iname().format(i)
                if not self.is_on_fastbus(name, i):
                    continue
                ret.append(self.data[name].extifinstance(name, i))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def extifdecl(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if not self.is_on_fastbus(name, i):
                    continue
                ret.append(self.data[name].extifdecl(name, i))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def slowifdeclmux(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                ret.append(self.data[name].slowifdeclmux(name, i))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def fastifdecl(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                print "fastifdecl", name, i, self.is_on_fastbus(name, i)
                if self.is_on_fastbus(name, i):
                    continue
                ret.append(self.data[name].fastifdecl(name, i))
        return '\n'.join(li(list(filter(None, ret)), 4))

    def slowifdecl(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                ret.append(self.data[name].slowifdecl().format(i, name))
        return '\n'.join(list(filter(None, ret)))

    def axi_reg_def(self, *args):
        ret = []
        start = 0x00011100  # start of AXI peripherals address
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                x = self.data[name].axi_reg_def(start, i)
                #print ("ifc", name, x)
                (rdef, offs) = x
                ret.append(rdef)
                start += offs
        return '\n'.join(list(filter(None, ret)))

    def _axi_num_idx(self, start, template, typ, idxtype, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                if typ == 'master':
                    fn = self.data[name].axi_master_idx
                else:
                    fn = self.data[name].axi_slave_idx
                (rdef, offs) = fn(start, i, idxtype)
                #print ("ifc", name, rdef, offs)
                ret.append(rdef)
                start += offs
        ret.append("typedef %d LastGen_%s_num;" % (start - 1, typ))
        decls = '\n'.join(list(filter(None, ret)))
        return template.format(decls)

    def axi_slave_idx(self, *args):
        return self._axi_num_idx(0, axi_slave_declarations, 'slave',
                                 '', *args)

    def axi_fastslave_idx(self, *args):
        return self._axi_num_idx(0, axi_fastslave_declarations, 'fastslave',
                                 'fast', *args)

    def axi_master_idx(self, *args):
        return self._axi_num_idx(2, axi_master_declarations, 'master',
                                 'master', *args)

    def axi_fastslave_idx(self, *args):
        return self._axi_num_idx(0, axi_fastslave_declarations, 'fastslave',
                                 'fast', *args)

    def axi_addr_map(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                ret.append(self.data[name].axi_addr_map(i))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def mkfast_peripheral(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                #print "mkfast", name, count
                x = self.data[name].mkfast_peripheral()
                print name, count, x
                suffix = self.data[name].mksuffix(name, i)
                ret.append(x.format(suffix))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def mkslow_peripheral(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                #print "mkslow", name, count
                x = self.data[name].mkslow_peripheral()
                print name, count, x
                suffix = self.data[name].mksuffix(name, i)
                ret.append(x.format(suffix))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def mk_fast_connection(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                txt = self.data[name].mk_connection(i, "fabric", "fast")
                if name == 'gpioa':
                    print "txt", txt
                    print self.data[name].mk_connection
                ret.append(txt)
        return '\n'.join(li(list(filter(None, ret)), 4))

    def mk_connection(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                txt = self.data[name].mk_connection(i, "slow_fabric", "")
                if name == 'gpioa':
                    print "txt", txt
                    print self.data[name].mk_connection
                ret.append(txt)
        return '\n'.join(li(list(filter(None, ret)), 8))

    def mk_cellconn(self):
        ret = []
        cellcount = 0
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                res = self.data[name].mk_cellconn(cellcount, name, i)
                if not res:
                    continue
                (txt, cellcount) = res
                ret.append(txt)
        ret = li('\n'.join(list(filter(None, ret))), 4)
        return li(pinmux_cellrule.format(ret), 4)

    def mk_pincon(self):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                txt = self.data[name].mk_pincon(name, i)
                ret.append(txt)
        return '\n'.join(li(list(filter(None, ret)), 4))

    def mk_dma_irq(self):
        ret = []
        sync = []
        rules = []
        cnct = []

        self.dma_count = 0

        for (name, count) in self.ifacecount:
            ifacerules = []
            for i in range(count):
                if not self.is_on_fastbus(name, i):
                    continue
                txt = self.data[name].mk_dma_sync(name, i)
                if txt:
                    self.dma_count += 1
                sync.append(txt)
                txt = self.data[name].mk_dma_rule(name, i)
                ifacerules.append(txt)
                txt = self.data[name].mk_dma_connect(name, i)
                cnct.append(txt)
            ifacerules = list(filter(None, ifacerules))
            if ifacerules:
                txt = "rule synchronize_%s_interrupts;" % name
                rules.append(txt)
                rules += ifacerules
                rules.append("endrule")

        cnct = list(filter(None, cnct))
        ct = self.dma_count
        _cnct    = ["rule rl_connect_interrupt_to_DMA;",
                    "  Bit #(%d) lv_interrupt_to_DMA={" % ct]
        spc = "                      "
        spcsep = ",\n" + spc
        cnct = _cnct + [spc + spcsep.join(cnct)]
        cnct.append("   };")
        cnct.append("   dma.interrupt_from_peripherals(\n" + \
                    "       lv_interrupt_to_DMA);")
        cnct.append("endrule;")

        ret = list(filter(None, sync + rules + cnct))
        ret = li(ret, 15)
        return '\n'.join(ret)

    def num_dmachannels(self):
        return "`define NUM_DMACHANNELS {0}".format(self.dma_count)

    def mk_ext_ifacedef(self):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                txt = self.data[name].mk_ext_ifacedef(name, i)
                ret.append(txt)
        return '\n'.join(li(list(filter(None, ret)), 8))

    def mk_plic(self):
        ret = []
        irq_offs = 8  # XXX: DMA scovers 0-7?
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                res = self.data[name].mk_plic(i, irq_offs)
                if not res:
                    continue
                (txt, irq_offs) = res
                ret.append(txt)
        self.num_slow_irqs = irq_offs
        return '\n'.join(li(list(filter(None, ret)), 4))

    def mk_sloirqsdef(self):
        return "    `define NUM_SLOW_IRQS {0}".format(self.num_slow_irqs)

    def is_on_fastbus(self, name, i):
        #print "fastbus mode", self.fastbusmode, name, i
        iname = self.data[name].iname().format(i)
        if self.fastbusmode:
            return iname not in self.fastbus
        return iname in self.fastbus


class PFactory(object):
    def getcls(self, name):
        from uart import uart
        from quart import quart
        from sdmmc import sdmmc
        from pwm import pwm
        from eint import eint
        from rs232 import rs232
        from twi import twi
        from eint import eint
        from jtag import jtag
        from spi import spi, mspi
        from qspi import qspi, mqspi
        from gpio import gpio
        from rgbttl import rgbttl

        for k, v in {'uart': uart,
                     'rs232': rs232,
                     'twi': twi,
                     'quart': quart,
                     'mqspi': mqspi,
                     'mspi': mspi,
                     'qspi': qspi,
                     'spi': spi,
                     'pwm': pwm,
                     'eint': eint,
                     'sd': sdmmc,
                     'jtag': jtag,
                     'lcd': rgbttl,
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
