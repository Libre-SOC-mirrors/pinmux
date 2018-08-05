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


class MMapConfig(object):

    def get_mmap_configs(self):
        res = []
        for cfg in self.peripheral.configs:
            res.append(cfg.get('mmap', None))
        # XXX HACK!  assume all configs same for each peripheral!
        return res[0]

    def map_to_idx(self, cfg, idx):
        if isinstance(idx, int):
            return idx
        for (i, c) in enumerate(cfg):
            if c[0] == idx:
                return i
        assert "config name %s not found" % s

    def get_mmap_cfg_start(self, idx):
        cfg = self.get_mmap_configs()
        if cfg is None:
            nregs = self.num_axi_regs32()
            if isinstance(nregs, int) or len(nregs) == 1:
                return 0
            return "_%d_" % idx
        idx = self.map_to_idx(cfg, idx)
        return cfg[idx][1]

    def get_mmap_cfg_name(self, idx):
        cfg = self.get_mmap_configs()
        if cfg is None:
            nregs = self.num_axi_regs32()
            if isinstance(nregs, int) or len(nregs) == 1:
                return ""
            return "_%d_" % idx
        return cfg[idx][0]

    def num_axi_regs32cfg(self):
        cfg = self.get_mmap_configs()
        if cfg is None:
            return self.num_axi_regs32()
        regs = []
        for c in cfg:
            regs.append(c[2])
        return regs


class PBase(MMapConfig):
    def __init__(self, name):
        self.name = name
        MMapConfig.__init__(self)

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
        template = "   {0}.send(\n" + \
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

    def axibase(self, name, ifacenum, idx):
        name = name.upper()
        return "%(name)s%(ifacenum)d%(idx)sBase" % locals()

    def axiend(self, name, ifacenum, idx):
        name = name.upper()
        return "%(name)s%(ifacenum)d%(idx)sEnd" % locals()

    def _axi_reg_def(self, idx, numregs, start, name, ifacenum):
        name = name.upper()
        offs = numregs * 4 * 16
        if offs == 0:
            return ('', 0)
        cfgstart = self.get_mmap_cfg_start(idx)
        if cfgstart:
            start = cfgstart
            end = start + offs - 1
            offs = 0  # don't do contiguous addressing
        else:
            end = start + offs - 1
        bname = self.axibase(name, ifacenum, idx)
        bend = self.axiend(name, ifacenum, idx)
        comment = "%d 32-bit regs" % numregs
        return ("`define %(bname)s 'h%(start)08X\n"
                "`define %(bend)s  'h%(end)08X // %(comment)s" % locals(),
                offs)

    def axi_reg_def(self, start, name, ifacenum):
        offs = self.num_axi_regs32cfg()
        if offs == 0:
            return ('', 0)
        if not isinstance(offs, list):
            offs = [offs]
        res = []
        offstotal = 0
        print offs
        for (idx, nregs) in enumerate(offs):
            cfg = self.get_mmap_cfg_name(idx)
            (txt, off) = self._axi_reg_def(cfg, nregs, start, name, ifacenum)
            start += off
            offstotal += off
            res.append(txt)
        return ('\n'.join(res), offstotal)

    def axi_master_name(self, name, ifacenum, typ=''):
        name = name.upper()
        return "{0}{1}_master_num".format(name, ifacenum)

    def axi_slave_name(self, idx, name, ifacenum, typ=''):
        name = name.upper()
        return "{0}{1}{3}_{2}slave_num".format(name, ifacenum, typ, idx)

    def axi_master_idx(self, idx, name, ifacenum, typ):
        name = self.axi_master_name(name, ifacenum, typ)
        return ("typedef {0} {1};".format(idx, name), 1)

    def axi_slave_idx(self, idx, name, ifacenum, typ):
        offs = self.num_axi_regs32()
        if offs == 0:
            return ''
        if not isinstance(offs, list):
            offs = [offs]
        res = []
        for (i, nregs) in enumerate(offs):
            cfg = self.get_mmap_cfg_name(i)
            name_ = self.axi_slave_name(cfg, name, ifacenum, typ)
            res.append("typedef {0} {1};".format(idx + i, name_))
        return ('\n'.join(res), len(offs))

    def axi_fastaddr_map(self, name, ifacenum):
        return self.axi_addr_map(name, ifacenum, 'fast')

    def _axi_addr_map(self, idx, name, ifacenum, typ=""):
        bname = self.axibase(name, ifacenum, idx)
        bend = self.axiend(name, ifacenum, idx)
        name = self.axi_slave_name(idx, name, ifacenum, typ)
        template = """\
if(addr>=`{0} && addr<=`{1})
    return tuple2(True,fromInteger(valueOf({2})));
else"""
        return template.format(bname, bend, name)

    def axi_addr_map(self, name, ifacenum, typ=""):
        offs = self.num_axi_regs32()
        if offs == 0:
            return ''
        if not isinstance(offs, list):
            offs = [offs]
        res = []
        for (idx, nregs) in enumerate(offs):
            cfg = self.get_mmap_cfg_name(idx)
            res.append(self._axi_addr_map(cfg, name, ifacenum, typ))
        return '\n'.join(res)

    def _mk_pincon(self, name, count, ptyp):
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
            if ptyp == 'fast':
                sname = self.get_iname(count)
                sname = "{0}.{1}".format(sname, pname)
                ps = "slow_peripherals.%s" % sname
            else:
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
                    cn = self._mk_actual_connection('out', name,
                                                    count, typ,
                                                    pname, ps_, n_, fname)
                    ret += cn
                fname = None
                if p.get('outen'):
                    fname = self.pinname_outen(pname)
                if fname:
                    if isinstance(fname, str):
                        fname = "{0}.{1}".format(n_, fname)
                    fname = self.pinname_tweak(pname, 'outen', fname)
                    cn = self._mk_actual_connection('outen', name,
                                                    count, typ,
                                                    pname, ps, n, fname)
                    ret += cn
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
                    cn = self._mk_actual_connection('in', name,
                                                    count, typ,
                                                    pname, ps_, n_, fname)
                    ret += cn
        return '\n'.join(ret)

    def _mk_vpincon(self, name, count, ptyp, typ, pname, stype=None):
        if stype is None:
            stype = pname
        ret = []
        ret.append("//%s %s %s %s %s" % (name, ptyp, typ, pname, stype))
        if ptyp == 'fast':
            sname = self.get_iname(count)
            ps = "slow_peripherals.%s" % sname
        else:
            sname = self.peripheral.iname().format(count)
            ps = "pinmux.peripheral_side.%s" % sname
        n = self.get_iname(count)
        if typ == 'in':
            n = "{0}.{1}".format(n, stype)
        ps_ = "{0}.{1}".format(ps, pname)
        ret += self._mk_actual_connection(typ, name, count, typ,
                                          pname, ps_, n, stype)
        return '\n'.join(ret)

    def _mk_actual_connection(self, ctype, name, count, typ,
                              pname, ps, n, fname):
        ret = []
        ck = self.get_clock_reset(name, count)
        if ctype == 'out':
            if ck == PBase.get_clock_reset(self, name, count):
                ret.append("mkConnection({0},\n\t\t\t{1}.{2});"
                           .format(ps, n, fname))
            else:
                n2 = "{0}{1}".format(name, count)
                sync = '{0}_{1}_sync'.format(n2, pname)
                ret.append("mkConnection({0},\n\t\t\t{1}.get);"
                           .format(ps, sync))
                ret.append("mkConnection({0}.put,\n\t\t\t{1}.{2});"
                           .format(sync, n, fname))
        elif ctype == 'outen':
            ret.append("mkConnection({0}_outen,\n\t\t\t{1});"
                       .format(ps, fname))
        elif ctype == 'in':
            if ck == PBase.get_clock_reset(self, name, count):
                ret.append("mkConnection({1},\n\t\t\t{0});".format(
                    ps, n))
            else:
                n2 = "{0}{1}".format(name, count)
                sync = '{0}_{1}_sync'.format(n2, pname)
                ret.append("mkConnection({1}.put,\n\t\t\t{0});".format(
                    ps, sync))
                ret.append("mkConnection({1},\n\t\t\t{0}.get);".format(
                    sync, n))
        return ret

    def _mk_clk_con(self, name, count, ctype):
        ret = []
        ck = self.get_clock_reset(name, count)
        if ck == PBase.get_clock_reset(self, name, count):
            return ''
        if ctype == 'slow':
            spc = self.get_clk_spc(ctype)
        else:
            spc = ck
            ck = self.get_clk_spc(ctype)
        template = "Ifc_sync#({0}) {1}_sync <-mksyncconnection(\n" + \
                   "              {2}, {3});"
        for p in self.peripheral.pinspecs:
            typ = p['type']
            pname = p['name']
            n = name
            if typ == 'out' or typ == 'inout':
                fname = self.pinname_out(pname)
                if not fname:
                    continue
                if not n.startswith('gpio'):  # XXX EURGH! horrible hack
                    n_ = "{0}{1}".format(n, count)
                else:
                    n_ = n
                n_ = '{0}_{1}'.format(n_, pname)
                ret.append(template.format("Bit#(1)", n_, ck, spc))
            if typ == 'in' or typ == 'inout':
                fname = self.pinname_in(pname)
                if not fname:
                    continue
                #fname = self.pinname_in(pname)
                n_ = "{0}{1}".format(n, count)
                n_ = '{0}_{1}'.format(n_, pname)
                #n_ = self.ifname_tweak(pname, 'in', n_)
                ret.append(template.format("Bit#(1)", n_, spc, ck))
        return '\n'.join(ret)

    def get_clk_spc(self, ctype):
        if ctype == 'slow':
            return "sp_clock, sp_reset"
        else:
            return "core_clock, core_reset"

    def _mk_clk_vcon(self, name, count, ctype, typ, pname, bitspec):
        ck = self.get_clock_reset(name, count)
        if ck == PBase.get_clock_reset(self, name, count):
            return ''
        if ctype == 'slow':
            spc = self.get_clk_spc(ctype)
        else:
            spc = ck
            ck = self.get_clk_spc(ctype)
        template = "Ifc_sync#({0}) {1}_sync <-mksyncconnection(\n" + \
                   "            {2}, {3});"""

        n_ = "{0}{1}".format(name, count)
        n_ = '{0}_{1}'.format(n_, pname)
        if typ == 'in' or typ == 'inout':
            ck, spc = spc, ck
        return template.format(bitspec, n_, ck, spc)

    def mk_cellconn(self, *args):
        return ''

    def mkfast_peripheral(self, size=0):
        return ''

    def mkslow_peripheral(self, size=0):
        return ''

    def mksuffix(self, name, i):
        return i

    def __mk_connection(self, con, aname, count, fabricname):
        txt = "mkConnection ({2}.v_to_slaves\n" + \
              "            [fromInteger(valueOf({1}))],\n" + \
              "            {0});"

        print "PBase __mk_connection", self.name, aname
        if not con:
            return ''
        con = con.format(count, aname)
        return txt.format(con, aname, fabricname)

    def __mk_master_connection(self, con, aname, count, fabricname):
        txt = "mkConnection ({0}, {2}.v_from_masters\n" + \
              "            [fromInteger(valueOf({1}))]);\n"

        print "PBase __mk_master_connection", self.name, aname
        if not con:
            return ''
        con = con.format(count, aname)
        return txt.format(con, aname, fabricname)

    def mk_master_connection(self, name, count, fabricname, typ):
        if not self.has_axi_master():
            return ''
        print "PBase mk_master_conn", self.name, count
        aname = self.axi_master_name(name, count, typ)
        ret = []
        connections = self._mk_connection(name, count, True)
        if not isinstance(connections, list):
            connections = [connections]
        for con in connections:
            ret.append(self.__mk_master_connection(con, aname, count,
                                                   fabricname))
        return '\n'.join(ret)

    def mk_connection(self, name, count, fabricname, typ, name_override=None):
        if name_override:  # needed for GPIO
            name = name_override
        print "PBase mk_conn", name, count
        ret = []
        connections = self._mk_connection(name, count)
        if not isinstance(connections, list):
            connections = [connections]
        for (idx, con) in enumerate(connections):
            cfg = self.get_mmap_cfg_name(idx)
            aname = self.axi_slave_name(cfg, name, count, typ)
            ret.append(self.__mk_connection(con, aname, count, fabricname))
        return '\n'.join(ret)

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

    def _extifinstance(self, name, count, suffix, prefix, samename=False,
                       ifsuffix=None):
        if ifsuffix is None:
            ifsuffix = ''
        pname = self.get_iname(count)
        if samename:
            sname = pname
        else:
            sname = self.peripheral.iname().format(count)
        template = "interface {0}{3} = {2}{1}{4};"
        return template.format(pname, sname, prefix, suffix, ifsuffix)

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

axi_master_declarations = """\
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
typedef  TAdd#(LastGen_fastslave_num,1)      Sdram_slave_num;
typedef  TAdd#(Sdram_slave_num   ,`ifdef SDRAM      1 `else 0 `endif )
                      Sdram_cfg_slave_num;
typedef TAdd#(Sdram_cfg_slave_num,`ifdef BOOTROM    1 `else 0 `endif )
                BootRom_slave_num   ;
typedef TAdd#(BootRom_slave_num  ,`ifdef Debug      1 `else 0 `endif )
                Debug_slave_num ;
typedef  TAdd#(Debug_slave_num   , `ifdef TCMemory  1 `else 0 `endif )
                TCM_slave_num;
typedef  TAdd#(TCM_slave_num     ,`ifdef DMA        1 `else 0 `endif )
                Dma_slave_num;
typedef  TAdd#(Dma_slave_num      ,1 )      SlowPeripheral_slave_num;
typedef  TAdd#(SlowPeripheral_slave_num,`ifdef VME  1 `else 0 `endif )
                VME_slave_num;
typedef TAdd#(VME_slave_num,1) Num_Fast_Slaves;
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
                      '_mk_clk_con', 'mk_ext_ifacedef',
                      'mk_connection', 'mk_master_connection',
                      'mk_cellconn', '_mk_pincon']:
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

    def axi_fastaddr_map(self, count):
        if not self.slow:
            return ''
        return self.slow.axi_fastaddr_map(self.ifacename, count)

    def axi_addr_map(self, count):
        if not self.slow:
            return ''
        return self.slow.axi_addr_map(self.ifacename, count)


class CallIfaceFn(object):
    def __init__(self, ifaces, kls, indent):
        self.ifaces = ifaces
        self.kls = kls
        self.indent = indent

    def __call__(self, ifaces, *args):
        ret = []
        for (name, count) in self.ifaces.ifacecount:
            print "CallIfaceFn", self.kls, self.ifaces
            print "CallIfaceFn args", name, count, args
            ret += list(self.kls(self.ifaces, name, count, *args))
        return '\n'.join(li(list(filter(None, ret)), self.indent))


class PeripheralInterfaces(object):
    def __init__(self):
        self.fastbusmode = False

        for (fname, kls, indent) in (
            ('_mk_connection', MkConnection, 8),
            ('_mk_pincon', MkPinCon, 4),
            ('_mk_clk_con', MkClkCon, 8),
            ('mk_ext_ifacedef', MkExtIface, 8),
        ):
            fn = CallIfaceFn(self, kls, indent)
            setattr(self, fname, types.MethodType(fn, self))

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
                if self.is_on_fastbus(name, i):
                    continue
                ret.append(self.data[name].extfastifinstance(name, i))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def extifinstance2(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                ret.append(self.data[name].extifinstance2(name, i))
        return '\n'.join(li(list(filter(None, ret)), 8))

    def extifinstance(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
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

    def axi_fastmem_def(self, *args):
        return self._axi_reg_def(0x50000000, *args)

    def axi_reg_def(self, *args):
        return self._axi_reg_def(0x00011100, *args)

    def _axi_reg_def(self, start, *args):
        ret = []
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

    def axi_fastaddr_map(self, *args):
        ret = []
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                ret.append(self.data[name].axi_fastaddr_map(i))
        return '\n'.join(li(list(filter(None, ret)), 8))

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

    def mk_master_connection(self, *args):
        return self._mk_connection("fabric", "fast", True, *args)

    def mk_fast_connection(self, *args):
        return self._mk_connection("fabric", "fast", False, *args)

    def mk_connection(self, *args):
        return self._mk_connection("slow_fabric", "", False, *args)

    def mk_cellconn(self):
        ret = []
        cellcount = 0
        for (name, count) in self.ifacecount:
            for i in range(count):
                if self.is_on_fastbus(name, i):
                    continue
                res = self.data[name].mk_cellconn(name, i, cellcount)
                if not res:
                    continue
                (txt, cellcount) = res
                ret.append(txt)
        ret = li('\n'.join(list(filter(None, ret))), 4)
        return li(pinmux_cellrule.format(ret), 4)

    def mk_pincon(self):
        return self._mk_pincon("slow")

    def mk_fast_pincon(self):
        return self._mk_pincon("fast")

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
        _cnct = ["rule rl_connect_interrupt_to_DMA;",
                 "  Bit #(%d) lv_interrupt_to_DMA={" % ct]
        spc = "                      "
        spcsep = ",\n" + spc
        cnct = _cnct + [spc + spcsep.join(cnct)]
        cnct.append("   };")
        cnct.append("   dma.interrupt_from_peripherals(\n" +
                    "       lv_interrupt_to_DMA);")
        cnct.append("endrule;")

        ret = list(filter(None, sync + rules + cnct))
        ret = li(ret, 15)
        return '\n'.join(ret)

    def num_dmachannels(self):
        return "`define NUM_DMACHANNELS {0}".format(self.dma_count)

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

    def mk_fastclk_con(self):
        return self._mk_clk_con("fast")

    def mk_slowclk_con(self):
        return self._mk_clk_con("slow")

    def is_on_fastbus(self, name, i):
        #print "fastbus mode", self.fastbusmode, name, i
        iname = self.data[name].iname().format(i)
        if self.fastbusmode:
            return iname not in self.fastbus
        return iname in self.fastbus


class IfaceIter(object):

    def __init__(self, ifaces, name, count, *args):
        self.ifaces = ifaces
        self.i = 0
        self.name = name
        self.maxcount = count
        self.args = args

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            if self.i >= self.maxcount:
                raise StopIteration
            if self.check(self.name, self.i):
                #print "iter", self.item
                #print "item args", self.args
                res = self.item(self.name, self.i, *self.args)
                if res:
                    self.i += 1
                    return res
            self.i += 1

    def next(self):
        return self.__next__()


class MkConnection(IfaceIter):

    def check(self, name, i):
        return not self.ifaces.is_on_fastbus(name, i)

    def item(self, name, i, fabric, typ, master):
        if master:
            return self.ifaces.data[name].mk_master_connection(name,
                                                               i, fabric, typ)
        return self.ifaces.data[name].mk_connection(name, i, fabric, typ)


class MkExtIface(IfaceIter):

    def check(self, name, i):
        return not self.ifaces.is_on_fastbus(name, i)

    def item(self, name, i):
        return self.ifaces.data[name].mk_ext_ifacedef(name, i)


class MkPinCon(IfaceIter):

    def check(self, name, i):
        return not self.ifaces.is_on_fastbus(name, i)

    def item(self, name, i, typ):
        return self.ifaces.data[name]._mk_pincon(name, i, typ)


class MkClkCon(IfaceIter):

    def check(self, name, i):
        return not self.ifaces.is_on_fastbus(name, i)

    def item(self, name, i, ctype):
        return self.ifaces.data[name]._mk_clk_con(name, i, ctype)


class PFactory(object):
    def getcls(self, name):
        from uart import uart
        from quart import quart
        from sdmmc import sdmmc
        from emmc import emmc
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
        from flexbus import flexbus
        from sdram import sdram

        for k, v in {'uart': uart,
                     'rs232': rs232,
                     'twi': twi,
                     'sdr': sdram,
                     'quart': quart,
                     'mqspi': mqspi,
                     'mspi': mspi,
                     'qspi': qspi,
                     'spi': spi,
                     'pwm': pwm,
                     'eint': eint,
                     'mmc': sdmmc,
                     'emmc': emmc,
                     'jtag': jtag,
                     'lcd': rgbttl,
                     'fb': flexbus,
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
