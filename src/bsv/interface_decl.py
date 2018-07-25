import os.path

try:
    from UserDict import UserDict
except ImportError:
    from collections import UserDict

from bsv.wire_def import generic_io  # special case
from bsv.wire_def import muxwire  # special case
from ifacebase import InterfacesBase
from bsv.peripheral_gen import PeripheralIface
from bsv.peripheral_gen import PeripheralInterfaces


class Pin(object):
    """ pin interface declaration.
        * name is the name of the pin
        * ready, enabled and io all create a (* .... *) prefix
        * action changes it to an "in" if true
    """

    def __init__(self, name,
                 name_=None,
                 idx=None,
                 ready=True,
                 enabled=True,
                 io=False,
                 action=False,
                 bitspec=None,
                 outenmode=False):
        self.name = name
        self.name_ = name_
        self.idx = idx
        self.ready = ready
        self.enabled = enabled
        self.io = io
        self.action = action
        self.bitspec = bitspec if bitspec else 'Bit#(1)'
        self.outenmode = outenmode

    # bsv will look like this (method declaration):
    """
    (*always_ready,always_enabled*) method Bit#(1) io0_cell_outen;
    (*always_ready,always_enabled,result="io"*) method
                       Action io0_inputval (Bit#(1) in);
    """

    def ifacepfmt(self, fmtfn):
        res = '          '
        status = []
        res += "interface "
        name = fmtfn(self.name_)
        if self.action:
            res += "Put"
        else:
            res += "Get"
        res += "#(%s) %s;" % (self.bitspec, name)
        return res

    def ifacefmt(self, fmtfn):
        res = '    '
        status = []
        if self.ready:
            status.append('always_ready')
        if self.enabled:
            status.append('always_enabled')
        if self.io:
            status.append('result="io"')
        if status:
            res += '(*'
            res += ','.join(status)
            res += '*)'
        res += " method "
        if self.io:
            res += "\n                      "
        name = fmtfn(self.name)
        if self.action:
            res += " Action "
            res += name
            res += ' (%s in)' % self.bitspec
        else:
            res += " %s " % self.bitspec
            res += name
        res += ";"
        return res

    def ifacedef(self, fmtoutfn, fmtinfn, fmtdecfn):
        res = '      method '
        if self.action:
            fmtname = fmtinfn(self.name)
            res += "Action  "
            res += fmtdecfn(self.name)
            res += '(%s in);\n' % self.bitspec
            res += '         %s<=in;\n' % fmtname
            res += '      endmethod'
        else:
            fmtname = fmtoutfn(self.name)
            res += "%s=%s;" % (self.name, fmtname)
        return res
    # sample bsv method definition :
    """
    method Action  cell0_mux(Bit#(2) in);
        wrcell0_mux<=in;
    endmethod
    """

    # sample bsv wire (wire definiton):
    """
    Wire#(Bit#(2)) wrcell0_mux<-mkDWire(0);
    """

    def wirefmt(self, fmtoutfn, fmtinfn, fmtdecfn):
        res = '      Wire#(%s) ' % self.bitspec
        if self.action:
            res += '%s' % fmtinfn(self.name)
        else:
            res += '%s' % fmtoutfn(self.name)
        res += "<-mkDWire(0);"
        return res

    def ifacedef2(self, fmtoutfn, fmtinfn, fmtdecfn):
        if self.action:
            fmtname = fmtinfn(self.name)
            res = "            interface %s = interface Put\n" % self.name_
            res += '              method '
            res += "Action put"
            #res += fmtdecfn(self.name)
            res += '(%s in);\n' % self.bitspec
            res += '                %s<=in;\n' % fmtname
            res += '              endmethod\n'
            res += '            endinterface;'
        else:
            fmtname = fmtoutfn(self.name)
            res = "            interface %s = interface Get\n" % self.name_
            res += '              method ActionValue#'
            res += '(%s) get;\n' % self.bitspec
            res += "                return %s;\n" % (fmtname)
            res += '              endmethod\n'
            res += '            endinterface;'
        return res

    def ifacedef3(self, idx, fmtoutfn, fmtinfn, fmtdecfn):
        if self.action:
            fmtname = fmtinfn(self.name)
            if self.name.endswith('outen'):
                name = "tputen"
            else:
                name = "tput"
            res = "                   %s <= in[%d];" % (fmtname, idx)
        else:
            fmtname = fmtoutfn(self.name)
            res = "                   tget[%d] = %s;" % (idx, fmtname)
            name = 'tget'
        return (name, res)


class Interface(PeripheralIface):
    """ create an interface from a list of pinspecs.
        each pinspec is a dictionary, see Pin class arguments
        single indicates that there is only one of these, and
        so the name must *not* be extended numerically (see pname)
    """
    # sample interface object:
    """
    twiinterface_decl = Interface('twi',
                                  [{'name': 'sda', 'outen': True},
                                   {'name': 'scl', 'outen': True},
                                   ])
    """

    def __init__(self, ifacename, pinspecs, ganged=None, single=False):
        PeripheralIface.__init__(self, ifacename)
        self.ifacename = ifacename
        self.ganged = ganged or {}
        self.pins = []  # a list of instances of class Pin
        self.pinspecs = pinspecs  # a list of dictionary
        self.single = single

        for idx, p in enumerate(pinspecs):
            _p = {}
            _p.update(p)
            if 'type' in _p:
                del _p['type']
            if p.get('outen') is True:  # special case, generate 3 pins
                del _p['outen']
                for psuffix in ['out', 'outen', 'in']:
                    # changing the name (like sda) to (twi_sda_out)
                    _p['name_'] = "%s_%s" % (p['name'], psuffix)
                    _p['name'] = "%s_%s" % (self.pname(p['name']), psuffix)
                    _p['action'] = psuffix != 'in'
                    _p['idx'] = idx
                    self.pins.append(Pin(**_p))
                    # will look like {'name': 'twi_sda_out', 'action': True}
                    # {'name': 'twi_sda_outen', 'action': True}
                    #{'name': 'twi_sda_in', 'action': False}
                    # NOTice - outen key is removed
            else:
                name = p['name']
                if name.isdigit():  # HACK!  deals with EINT case
                    name = self.pname(name)
                _p['name_'] = name
                _p['idx'] = idx
                _p['name'] = self.pname(p['name'])
                self.pins.append(Pin(**_p))

    # sample interface object:
    """
        uartinterface_decl = Interface('uart',
                                   [{'name': 'rx'},
                                    {'name': 'tx', 'action': True},
                                    ])
    """
    """
    getifacetype is called multiple times in actual_pinmux.py
    x = ifaces.getifacetype(temp), where temp is uart_rx, spi_mosi
    Purpose is to identify is function : input/output/inout
    """

    def getifacetype(self, name):
        for p in self.pinspecs:
            fname = "%s_%s" % (self.ifacename, p['name'])
            # print "search", self.ifacename, name, fname
            if fname == name:
                if p.get('action'):
                    return 'out'
                elif p.get('outen'):
                    return 'inout'
                return 'input'
        return None

    def iname(self):
        """ generates the interface spec e.g. flexbus_ale
            if there is only one flexbus interface, or
            sd{0}_cmd if there are several.  string format
            function turns this into sd0_cmd, sd1_cmd as
            appropriate.  single mode stops the numerical extension.
        """
        if self.single:
            return self.ifacename
        return '%s{0}' % self.ifacename

    def pname(self, name):
        """ generates the interface spec e.g. flexbus_ale
            if there is only one flexbus interface, or
            sd{0}_cmd if there are several.  string format
            function turns this into sd0_cmd, sd1_cmd as
            appropriate.  single mode stops the numerical extension.
        """
        return "%s_%s" % (self.iname(), name)

    def busfmt(self, *args):
        """ this function creates a bus "ganging" system based
            on input from the {interfacename}.txt file.
            only inout pins that are under the control of the
            interface may be "ganged" together.
        """
        if not self.ganged:
            return ''  # when self.ganged is None
        # print self.ganged
        res = []
        for (k, pnames) in self.ganged.items():
            name = self.pname('%senable' % k).format(*args)
            decl = 'Bit#(1) %s = 0;' % name
            res.append(decl)
            ganged = []
            for p in self.pinspecs:
                if p['name'] not in pnames:
                    continue
                pname = self.pname(p['name']).format(*args)
                if p.get('outen') is True:
                    outname = self.ifacefmtoutfn(pname)
                    ganged.append("%s_outen" % outname)  # match wirefmt

            gangedfmt = '{%s} = duplicate(%s);'
            res.append(gangedfmt % (',\n  '.join(ganged), name))
        return '\n'.join(res) + '\n\n'

    def wirefmt(self, *args):
        res = '\n'.join(map(self.wirefmtpin, self.pins)).format(*args)
        res += '\n'
        return '\n' + res

    def ifacepfmt(self, *args):
        res = '\n'.join(map(self.ifacepfmtdecpin, self.pins)).format(*args)
        return '\n' + res  # pins is a list

    def ifacefmt(self, *args):
        res = '\n'.join(map(self.ifacefmtdecpin, self.pins)).format(*args)
        return '\n' + res  # pins is a list

    def ifacepfmtdecfn(self, name):
        return name

    def ifacefmtdecfn(self, name):
        return name  # like: uart

    def ifacefmtdecfn2(self, name):
        return name  # like: uart

    def ifacefmtdecfn3(self, name):
        """ HACK! """
        return "%s_outen" % name  # like uart_outen

    def ifacefmtoutfn(self, name):
        return "wr%s" % name  # like wruart

    def ifacefmtinfn(self, name):
        return "wr%s" % name

    def wirefmtpin(self, pin):
        return pin.wirefmt(self.ifacefmtoutfn, self.ifacefmtinfn,
                           self.ifacefmtdecfn2)

    def ifacepfmtdecpin(self, pin):
        return pin.ifacepfmt(self.ifacepfmtdecfn)

    def ifacefmtdecpin(self, pin):
        return pin.ifacefmt(self.ifacefmtdecfn)

    def ifacefmtpin(self, pin):
        decfn = self.ifacefmtdecfn2
        outfn = self.ifacefmtoutfn
        # print pin, pin.outenmode
        if pin.outenmode:
            decfn = self.ifacefmtdecfn3
            outfn = self.ifacefmtoutenfn
        return pin.ifacedef(outfn, self.ifacefmtinfn,
                            decfn)

    def ifacedef2pin(self, pin):
        decfn = self.ifacefmtdecfn2
        outfn = self.ifacefmtoutfn
        # print pin, pin.outenmode
        if pin.outenmode:
            decfn = self.ifacefmtdecfn3
            outfn = self.ifacefmtoutenfn
        return pin.ifacedef2(outfn, self.ifacefmtinfn,
                             decfn)

    def ifacedef(self, *args):
        res = '\n'.join(map(self.ifacefmtpin, self.pins))
        res = res.format(*args)
        return '\n' + res + '\n'

    def ifacedef2(self, *args):
        res = '\n'.join(map(self.ifacedef2pin, self.pins))
        res = res.format(*args)
        return '\n' + res + '\n'

    def vectorifacedef2(self, pins, count, names, bitfmt, *args):
        tput = []
        tget = []
        tputen = []
        # XXX HACK! assume in, out and inout, create set of indices
        # that are repeated three times.
        plens = []
        # ARG even worse hack for LCD *sigh*...
        if names[1] is None and names[2] is None:
            plens = range(len(pins))
        else:
            for i in range(0, len(pins), 3):
                plens += [i / 3, i / 3, i / 3]
        for (typ, txt) in map(self.ifacedef3pin, plens, pins):
            if typ == 'tput':
                tput.append(txt)
            elif typ == 'tget':
                tget.append(txt)
            elif typ == 'tputen':
                tputen.append(txt)
        tput = '\n'.join(tput).format(*args)
        tget = '\n'.join(tget).format(*args)
        tputen = '\n'.join(tputen).format(*args)
        bitfmt = bitfmt.format(count)
        template = ["""\
              interface {3} = interface Put#({0})
                 method Action put({2} in);
{1}
                 endmethod
               endinterface;
""",
                    """\
               interface {3} = interface Put#({0})
                 method Action put({2} in);
{1}
                 endmethod
               endinterface;
""",
                    """\
               interface {3} = interface Get#({0})
                 method ActionValue#({2}) get;
                   {2} tget;
{1}
                   return tget;
                 endmethod
               endinterface;
"""]
        res = ''
        tlist = [tput, tputen, tget]
        for i, n in enumerate(names):
            if n:
                res += template[i].format(count, tlist[i], bitfmt, n)
        return '\n' + res + '\n'


class MuxInterface(Interface):

    def wirefmt(self, *args):
        return muxwire.format(*args)


class IOInterface(Interface):

    def ifacefmtoutenfn(self, name):
        return "cell{0}_mux_outen"

    def ifacefmtoutfn(self, name):
        """ for now strip off io{0}_ part """
        return "cell{0}_mux_out"

    def ifacefmtinfn(self, name):
        return "cell{0}_mux_in"

    def wirefmt(self, *args):
        return generic_io.format(*args)


class InterfaceBus(object):

    def __init__(self, namelist, bitspec, filterbus):
        self.namelist = namelist
        self.bitspec = bitspec
        self.fbus = filterbus  # filter identifying which are bus pins

    def get_nonbuspins(self):
        return filter(lambda x: not x.name_.startswith(self.fbus), self.pins)

    def get_buspins(self):
        return filter(lambda x: x.name_.startswith(self.fbus), self.pins)

    def ifacepfmt(self, *args):
        pins = self.get_nonbuspins()
        res = '\n'.join(map(self.ifacepfmtdecpin, pins)).format(*args)
        res = res.format(*args)

        pins = self.get_buspins()
        plen = self.get_n_iopins(pins)

        res += '\n'
        template = "          interface {1}#(%s) {2};\n" % self.bitspec
        for i, n in enumerate(self.namelist):
            if not n:
                continue
            ftype = 'Get' if i == 2 else "Put"
            res += template.format(plen, ftype, n)

        return "\n" + res

    def ifacedef2(self, *args):
        pins = self.get_nonbuspins()
        res = '\n'.join(map(self.ifacedef2pin, pins))
        res = res.format(*args)

        pins = self.get_buspins()
        plen = self.get_n_iopins(pins)
        bitspec = self.bitspec.format(plen)
        return '\n' + res + self.vectorifacedef2(
            pins, plen, self.namelist, bitspec, *args) + '\n'

    def ifacedef3pin(self, idx, pin):
        decfn = self.ifacefmtdecfn2
        outfn = self.ifacefmtoutfn
        # print pin, pin.outenmode
        if pin.outenmode:
            decfn = self.ifacefmtdecfn3
            outfn = self.ifacefmtoutenfn
        return pin.ifacedef3(idx, outfn, self.ifacefmtinfn,
                             decfn)


class InterfaceLCD(InterfaceBus, Interface):

    def __init__(self, *args):
        InterfaceBus.__init__(self, ['data_out', None, None],
                              "Bit#({0})", "out")
        Interface.__init__(self, *args)

    def get_n_iopins(self, pins):  # HACK! assume in/out/outen so div by 3
        return len(pins)


class InterfaceSD(InterfaceBus, Interface):

    def __init__(self, *args):
        InterfaceBus.__init__(self, ['out', 'out_en', 'in'],
                              "Bit#({0})", "d")
        Interface.__init__(self, *args)

    def get_n_iopins(self, pins):  # HACK! assume in/out/outen so div by 3
        return len(pins) / 3


class InterfaceNSPI(InterfaceBus, Interface):

    def __init__(self, *args):
        InterfaceBus.__init__(self, ['io_out', 'io_out_en', 'io_in'],
                              "Bit#({0})", "io")
        Interface.__init__(self, *args)

    def get_n_iopins(self, pins):  # HACK! assume in/out/outen so div by 3
        return len(pins) / 3


class InterfaceEINT(Interface):
    """ uses old-style (non-get/put) for now
    """

    def ifacepfmt(self, *args):
        res = '\n'.join(map(self.ifacefmtdecpin, self.pins)).format(*args)
        return '\n' + res  # pins is a list

    def ifacedef2(self, *args):
        return self.ifacedef(*args)


class InterfaceGPIO(InterfaceBus, Interface):
    """ note: the busfilter cuts out everything as the entire set of pins
        is a bus, but it's less code.  get_nonbuspins returns empty list.
    """

    def __init__(self, ifacename, pinspecs, ganged=None, single=False):
        InterfaceBus.__init__(self, ['out', 'out_en', 'in'],
                              "Vector#({0},Bit#(1))", ifacename[-1])
        Interface.__init__(self, ifacename, pinspecs, ganged, single)

    def get_n_iopins(self, pins):  # HACK! assume in/out/outen so div by 3
        return len(pins) / 3


class Interfaces(InterfacesBase, PeripheralInterfaces):
    """ contains a list of interface definitions
    """

    def __init__(self, pth=None):
        InterfacesBase.__init__(self, Interface, pth,
                                {'gpio': InterfaceGPIO,
                                 'spi': InterfaceNSPI,
                                 'mspi': InterfaceNSPI,
                                 'lcd': InterfaceLCD,
                                 'sd': InterfaceSD,
                                 'qspi': InterfaceNSPI,
                                 'mqspi': InterfaceNSPI,
                                 'eint': InterfaceEINT})
        PeripheralInterfaces.__init__(self)

    def ifacedef(self, f, *args):
        for (name, count) in self.ifacecount:
            for i in range(count):
                f.write(self.data[name].ifacedef(i))

    def ifacedef2(self, f, *args):
        c = "        interface {0} = interface PeripheralSide{1}"
        for (name, count) in self.ifacecount:
            for i in range(count):
                iname = self.data[name].iname().format(i)
                f.write(c.format(iname, name.upper()))
                f.write(self.data[name].ifacedef2(i))
                f.write("        endinterface;\n\n")

    def busfmt(self, f, *args):
        f.write("import BUtils::*;\n\n")
        for (name, count) in self.ifacecount:
            for i in range(count):
                bf = self.data[name].busfmt(i)
                f.write(bf)

    def ifacepfmt(self, f, *args):
        comment = '''
      // interface declaration between {0} and pinmux
      (*always_ready,always_enabled*)
      interface PeripheralSide{0};'''
        for (name, count) in self.ifacecount:
            f.write(comment.format(name.upper()))
            f.write(self.data[name].ifacepfmt(0))
            f.write("\n      endinterface\n")

    def ifacefmt(self, f, *args):
        comment = '''
          // interface declaration between %s-{0} and pinmux'''
        for (name, count) in self.ifacecount:
            for i in range(count):
                c = comment % name.upper()
                f.write(c.format(i))
                f.write(self.data[name].ifacefmt(i))

    def ifacefmt2(self, f, *args):
        comment = '''
            interface PeripheralSide{0} {1};'''
        for (name, count) in self.ifacecount:
            for i in range(count):
                iname = self.data[name].iname().format(i)
                f.write(comment.format(name.upper(), iname))

    def wirefmt(self, f, *args):
        comment = '\n      // following wires capture signals ' \
                  'to IO CELL if %s-{0} is\n' \
                  '      // allotted to it'
        for (name, count) in self.ifacecount:
            for i in range(count):
                c = comment % name
                f.write(c.format(i))
                f.write(self.data[name].wirefmt(i))


# ========= Interface declarations ================ #

mux_interface = MuxInterface('cell',
                             [{'name': 'mux', 'ready': False, 'enabled': False,
                               'bitspec': '{1}', 'action': True}])

io_interface = IOInterface(
    'io',
    [{'name': 'cell_out', 'enabled': True, },
     {'name': 'cell_outen', 'enabled': True, 'outenmode': True, },
     {'name': 'cell_in', 'action': True, 'io': True}, ])

# == Peripheral Interface definitions == #
# these are the interface of the peripherals to the pin mux
# Outputs from the peripherals will be inputs to the pinmux
# module. Hence the change in direction for most pins

# ======================================= #

# basic test
if __name__ == '__main__':

    uartinterface_decl = Interface('uart',
                                   [{'name': 'rx'},
                                    {'name': 'tx', 'action': True},
                                    ])

    twiinterface_decl = Interface('twi',
                                  [{'name': 'sda', 'outen': True},
                                   {'name': 'scl', 'outen': True},
                                   ])

    def _pinmunge(p, sep, repl, dedupe=True):
        """ munges the text so it's easier to compare.
            splits by separator, strips out blanks, re-joins.
        """
        p = p.strip()
        p = p.split(sep)
        if dedupe:
            p = filter(lambda x: x, p)  # filter out blanks
        return repl.join(p)

    def pinmunge(p):
        """ munges the text so it's easier to compare.
        """
        # first join lines by semicolons, strip out returns
        p = p.split(";")
        p = map(lambda x: x.replace('\n', ''), p)
        p = '\n'.join(p)
        # now split first by brackets, then spaces (deduping on spaces)
        p = _pinmunge(p, "(", " ( ", False)
        p = _pinmunge(p, ")", " ) ", False)
        p = _pinmunge(p, " ", " ")
        return p

    def zipcmp(l1, l2):
        l1 = l1.split("\n")
        l2 = l2.split("\n")
        for p1, p2 in zip(l1, l2):
            print (repr(p1))
            print (repr(p2))
            print ()
            assert p1 == p2

    ifaces = Interfaces()

    ifaceuart = ifaces['uart']
    print (ifaceuart.ifacedef(0))
    print (uartinterface_decl.ifacedef(0))
    assert ifaceuart.ifacedef(0) == uartinterface_decl.ifacedef(0)

    ifacetwi = ifaces['twi']
    print (ifacetwi.ifacedef(0))
    print (twiinterface_decl.ifacedef(0))
    assert ifacetwi.ifacedef(0) == twiinterface_decl.ifacedef(0)
