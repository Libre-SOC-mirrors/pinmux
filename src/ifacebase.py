import os.path

try:
    from UserDict import UserDict
except ImportError:
    from collections import UserDict


class InterfacesBase(UserDict):
    """ contains a list of interface definitions
    """

    def __init__(self, ifacekls, pth=None, ifaceklsdict=None):
        self.pth = pth
        self.fastbus = []
        self.ifacecount = []
        if ifaceklsdict is None:
            ifaceklsdict = {}
        UserDict.__init__(self, {})
        if not pth:
            return
        ift = 'interfaces.txt'
        if pth:
            ift = os.path.join(pth, ift)
        with open(ift, 'r') as ifile:
            for ln in ifile.readlines():
                ln = ln.strip()
                ln = ln.split("\t")
                name = ln[0]  # will have uart
                count = int(ln[1])  # will have count of uart
                self.fastbus += ln[2:]
                # spec looks like this:
                """
                [{'name': 'sda', 'outen': True},
                 {'name': 'scl', 'outen': True},
                ]
                """
                ikls = ifacekls
                for k, v in ifaceklsdict.items():
                    if name.startswith(k):
                        ikls = v
                        break
                spec, ganged = self.read_spec(pth, name)
                # XXX HORRIBLE hack!!!
                if name == 'pwm' and count == 1 and len(spec) != 1:
                    #print "read", name, count, spec, ganged
                    #print "multi pwm", spec[:1], len(spec)
                    spec[0]['name'] = 'out'
                    iface = ikls(name, spec[:1], ganged, False)
                    self.ifaceadd(name, len(spec), iface)
                else:
                    iface = ikls(name, spec, ganged, count == 1)
                    self.ifaceadd(name, count, iface)

    def getifacetype(self, fname):
        # finds the interface type, e.g sd_d0 returns "inout"
        for iface in self.values():
            typ = iface.getifacetype(fname)
            # if fname.startswith('pwm'):
            #   print fname, iface.ifacename, typ
            if typ:
                return typ
        return None

    def ifaceadd(self, name, count, iface, at=None):
        if at is None:
            at = len(self.ifacecount)  # ifacecount is a list
        self.ifacecount.insert(at, (name, count))  # appends the list
        # with (name,count) *at* times
        self[name] = iface

    """
    will check specific files of kind peripheral.txt like spi.txt,
    uart.txt in test directory
    """

    def read_spec(self, pth, name):
        spec = []
        ganged = {}
        fname = '%s.txt' % name
        if pth:
            ift = os.path.join(pth, fname)
        with open(ift, 'r') as sfile:
            for ln in sfile.readlines():
                ln = ln.strip()
                ln = ln.split("\t")
                name = ln[0]
                d = {'name': name,  # here we start to make the dictionary
                     'type': ln[1]}
                if ln[1] == 'out':
                    d['action'] = True  # adding element to the dict
                elif ln[1] == 'inout':
                    d['outen'] = True
                    if len(ln) == 3:
                        bus = ln[2]
                        if bus not in ganged:
                            ganged[bus] = []
                        ganged[bus].append(name)
                spec.append(d)
        return spec, ganged
